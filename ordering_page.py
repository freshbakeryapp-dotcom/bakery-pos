import streamlit as st
from utils.ordering import get_order_recommendations
from utils.export import generate_order_text, generate_pdf_bytes
from db import get_db
import time

st.set_page_config(page_title="Smart Ordering - Artisan Crumb", layout="wide")

st.markdown('<h1 style="font-family: \'Playfair Display\', serif;">📦 Smart Reorder</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #6B5444;">AI-calculated orders based on production plans + actual usage variance.</p>', unsafe_allow_html=True)

# --- Simulation Trigger ---
conn = get_db()
plans_count = conn.execute("SELECT count(*) FROM production_plans").fetchone()[0]
conn.close()

if plans_count == 0:
    st.warning("⚠️ No production plans found. AI needs a schedule to calculate orders.")
    if st.button("🧪 Simulate Next Week (Demo)", type="secondary"):
        import sqlite3
        conn = sqlite3.connect('bakery.db')
        prod = conn.execute("SELECT id FROM products LIMIT 1").fetchone()
        if prod:
            conn.executemany("INSERT INTO production_plans (product_id, quantity, scheduled_date) VALUES (?, 25, date('now', '+' || ? || ' days'))", [(prod[0], i) for i in range(1, 8)])
            conn.executemany('UPDATE ingredients SET target_stock=?, cost_per_unit=0.005 WHERE name=?', [(3000, 'Flour'), (1500, 'Butter'), (800, 'Sugar')])
            conn.commit()
            st.success("✅ Simulation started! Refreshing...")
            time.sleep(1)
            st.rerun()
        conn.close()
    st.stop()

# --- Main Logic ---
recs = get_order_recommendations(days_ahead=7)

if not recs:
    st.success("✅ Stock levels are healthy! No orders needed right now.")
    st.stop()

# --- Order Cards ---
st.subheader(" Recommended Orders")

# Batch selection
selected_ids = []
for rec in recs:
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown(f"**{rec['name']}**")
        st.caption(f"Current: {rec['current_stock']} {rec['unit']}")
    with col2:
        st.metric("Need", f"{rec['recommended_order']} {rec['unit']}")
        st.caption(f"Variance: {int((rec['variance_coeff']-1)*100)}% | Conf: {rec['confidence']}%")
    with col3:
        include = st.checkbox("Include", value=True, key=f"chk_{rec['id']}")
        if include:
            selected_ids.append(rec)

# --- Actions ---
if selected_ids:
    st.markdown("---")
    st.subheader(" Send to Supplier")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    # 1. WhatsApp Copy
    with col_btn1:
        wa_text = generate_order_text(selected_ids)
        if st.button(" Copy for WhatsApp", use_container_width=True):
            st.code(wa_text)
            st.success("Text copied to clipboard area above! Ctrl+C to copy.")
            
    # 2. Email Draft
    with col_btn2:
        email_text = generate_order_text(selected_ids).replace("*", "")
        if st.button(" Copy for Email", use_container_width=True):
            st.code(email_text)
            st.success("Email body copied!")
            
    # 3. PDF Download
    with col_btn3:
        pdf_bytes = generate_pdf_bytes(selected_ids)
        if pdf_bytes:
            st.download_button(
                label="📄 Download PDF",
                data=pdf_bytes,
                file_name=f"PO_{st.session_state.get('store', 'Bakery')}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.button(" Download PDF (Install fpdf)", disabled=True, use_container_width=True)
            
    # 4. Confirm & Update Stock
    if st.button("✅ Confirm Orders & Update Stock", type="primary", use_container_width=True):
        # In a real app, this would log the PO. Here we simulate stock receipt.
        import sqlite3
        conn = sqlite3.connect('bakery.db')
        for item in selected_ids:
            # Update stock (Simulating delivery arrival)
            conn.execute("UPDATE ingredients SET current_stock = current_stock + ? WHERE id = ?", (item['recommended_order'], item['id']))
            # Log transaction
            conn.execute("INSERT INTO inventory_transactions (ingredient_id, type, quantity, reference_id) VALUES (?, 'purchase', ?, ?)", (item['id'], item['recommended_order'], item['id']))
        conn.commit()
        conn.close()
        st.success("✅ Orders confirmed! Stock levels updated.")
        st.balloons()
        time.sleep(1)
        st.rerun()
else:
    st.info(" No ingredients selected. Check all to order.")