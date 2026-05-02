import streamlit as st
from utils.prep import get_todays_prep_list, start_batch, complete_batch
from datetime import datetime
import sqlite3
from db import get_db

st.set_page_config(page_title="Today's Bake Sheet", layout="wide")

st.markdown(f'<h1 style="font-family: \'Playfair Display\', serif;"> Today\'s Prep List</h1>', unsafe_allow_html=True)
st.markdown(f'<p style="color: #6B5444;">{datetime.now().strftime("%A, %B %d, %Y")} • AI-Optimized Schedule</p>', unsafe_allow_html=True)

# Show feedback messages
if 'last_action' in st.session_state:
    if st.session_state.last_action == 'started':
        st.success(f"✅ Batch started! Deducted ingredients. Run ID: {st.session_state.last_run_id}")
    elif st.session_state.last_action == 'completed':
        st.success(f"✅ Batch #{st.session_state.last_run_id} completed!")
    # Clear the message after showing
    del st.session_state.last_action

prep_list = get_todays_prep_list()

if not prep_list:
    st.info("📭 No production scheduled for today.")
    st.stop()

conn = get_db()

# --- 1. LIVE INGREDIENT STATUS ---
st.subheader(" Ingredient Stock Check")
all_ingredients = {}
for item in prep_list:
    for ing in item["ingredients"]:
        name = ing["name"]
        if name not in all_ingredients:
            all_ingredients[name] = {"needed": 0, "unit": ing["unit"]}
        all_ingredients[name]["needed"] += ing["needed_grams"]

# Get current stock for display
stock_data = {}
for ing_name in all_ingredients.keys():
    row = conn.execute("SELECT current_stock FROM ingredients WHERE name=?", (ing_name,)).fetchone()
    stock_data[ing_name] = row[0] if row else 0

cols = st.columns(4)
for i, (name, data) in enumerate(all_ingredients.items()):
    with cols[i % 4]:
        needed = data["needed"]
        current = stock_data.get(name, 0)
        status = "✅ OK" if current >= needed else "⚠️ LOW STOCK"
        
        st.metric(name, f"{needed} {data['unit']} needed", delta=status)
        st.caption(f"Current Stock: {current} {data['unit']}")

st.markdown("---")

# --- 2. BATCH QUEUE ---
st.subheader(" Batch Queue")
completed_runs_shown = set()

for item in prep_list:
    unique_key = item['item_id'] 
    
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            st.markdown(f"### {item['product_name']}")
            st.caption(f"Target: {item['target_qty']} units")
            
        with col2:
            st.markdown("**Ingredients:**")
            if item['ingredients']:
                ing_text = " • ".join([f"{i['name']}: {i['needed_grams']:.0f}g" for i in item['ingredients']])
                st.markdown(f"<div style='font-size: 0.9rem; color: #6B5444;'>{ing_text}</div>", unsafe_allow_html=True)
            
            # Show Active Run Status
            active = conn.execute("SELECT id FROM production_runs WHERE product_id=? AND status='in_progress'", (item["product_id"],)).fetchone()
            if active:
                st.markdown(f"🔄 **Batch #{active['id']} In Progress**")
                
        with col3:
            if active:
                if active['id'] not in completed_runs_shown:
                    if st.button("✅ Complete", key=f"done_{active['id']}", type="primary", use_container_width=True):
                        complete_batch(active['id'])
                        st.session_state.last_action = 'completed'
                        st.session_state.last_run_id = active['id']
                        st.rerun()
                    completed_runs_shown.add(active['id'])
            else:
                # DEBUG: Show what we're about to send
                st.caption(f"ID: {unique_key}, Prod: {item['product_id']}")
                
                if st.button("▶️ Start", key=f"start_{unique_key}", use_container_width=True):
                    try:
                        run_id = start_batch(item["item_id"], item["product_id"], item["target_qty"])
                        st.session_state.last_action = 'started'
                        st.session_state.last_run_id = run_id
                        st.success(f"✅ Started batch #{run_id}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# --- 3. RECENT ACTIVITY LOG ---
st.markdown("---")
st.subheader("📝 Recent Production Log")
recent_runs = conn.execute("""
    SELECT pr.id, p.name, pr.quantity_baked, pr.status, pr.completed_at
    FROM production_runs pr
    JOIN products p ON pr.product_id = p.id
    ORDER BY pr.id DESC LIMIT 5
""").fetchall()

if recent_runs:
    for run in recent_runs:
        status_icon = "✅" if run['status'] == 'completed' else "🔄"
        time_str = run['completed_at'] if run['completed_at'] else "Started just now"
        st.caption(f"{status_icon} **Batch #{run['id']}**: {run['name']} ({run['quantity_baked']} units) — {time_str}")
else:
    st.caption("No recent activity.")

conn.close()