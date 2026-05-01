import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row
# Migrate old database schema
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN actually_produced INTEGER")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN waste_reason TEXT DEFAULT 'overproduction'")
except:
    pass
try:
    conn.execute("SELECT actually_sold FROM plan_items LIMIT 1")
except:
    conn.execute("ALTER TABLE plan_items ADD COLUMN actually_sold INTEGER")
latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

from db import init_db
init_db()
# ============================================================
# MODE 1: NO FORECAST — Setup
# ============================================================
if not latest_plan:
    st.warning("⚠️ No forecast yet.")
    
    date_count = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
    total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
    
    st.write(f"📅 Unique sale dates: **{date_count}** (need 3+)")
    st.write(f"📦 Total sales rows: **{total_sales}**")
    
    if date_count >= 3:
        if st.button("🔄 Train AI from Existing Sales", type="primary"):
            from engine import train_all_models, generate_forecast, save_forecast_to_db
            with st.spinner("Training..."):
                count = train_all_models()
                if count > 0:
                    forecast = generate_forecast()
                    save_forecast_to_db(forecast)
                    st.success(f"✅ Trained {count} models!")
                    st.rerun()
                else:
                    st.error("Training failed.")
    
    st.markdown("---")
    st.subheader("🚀 Import Historical CSV")
    csv_file = st.file_uploader("Upload POS CSV", type=["csv"], key="csv_import")
    
    if csv_file is not None:
        raw_df = pd.read_csv(csv_file)
        st.success(f"✅ {len(raw_df)} rows loaded")
        
        if st.button("📥 Import & Train AI", type="primary", key="do_import_v3"):
            inserted = 0
            with st.spinner("Importing..."):
                for _, row in raw_df.iterrows():
                    product_name = str(row.get('product', '')).strip()
                    store = str(row.get('store', 'Gadong')).strip()
                    qty = int(row.get('quantity_sold', row.get('qty', 1)))
                    price = float(row.get('unit_price', row.get('price', 3.0)))
                    date_raw = str(row['date']).strip()
                    
                    try:
                        date_val = pd.to_datetime(date_raw).strftime("%Y-%m-%d")
                    except:
                        continue
                    
                    product_match = conn.execute(
                        "SELECT id FROM products WHERE LOWER(name) = LOWER(?)",
                        (product_name,)
                    ).fetchone()
                    
                    if not product_match:
                        conn.execute(
                            "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
                            (product_name, "Imported", price)
                        )
                        product_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    else:
                        product_id = product_match['id']
                    
                    conn.execute(
                        "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (product_id, store, qty, price, qty * price, f"{date_val} 10:00:00")
                    )
                    inserted += 1
            
            conn.commit()
            date_count = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
            st.success(f"✅ Imported {inserted} rows. Unique dates: {date_count}")
            
            if date_count >= 3:
                from engine import train_all_models, generate_forecast, save_forecast_to_db
                with st.spinner("Training..."):
                    count = train_all_models()
                    if count > 0:
                        forecast = generate_forecast()
                        save_forecast_to_db(forecast)
                        st.success(f"🎉 {count} models trained!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Training failed.")
            else:
                st.error(f"Need 3+ unique dates. You have {date_count}.")

# ============================================================
# MODE 2: FORECAST EXISTS
# ============================================================
else:
    plan_date = latest_plan['date']
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if plan_date == today:
        st.success(f"✅ Today's Plan — {plan_date}")
    elif plan_date == tomorrow:
        st.info(f"📋 Tomorrow's Plan — {plan_date}")
    else:
        st.warning(f"⚠️ Plan for {plan_date}")
    
    items = conn.execute("""
        SELECT pi.id as item_id, pi.ai_recommended, pi.baker_override,
               pi.actually_produced, pi.wasted, pi.waste_reason,
               p.name as product, p.id as product_id
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
        ORDER BY p.name
    """, (latest_plan['id'],)).fetchall()
    
    if items:
        # ---- MORNING: Production Plan with Overrides ----
        st.subheader("🌅 Morning: Set Today's Production")
        st.caption("Override the AI recommendations with what you'll actually bake.")
        
        for item in items:
            cols = st.columns([2, 1, 1])
            cols[0].write(f"**{item['product']}**")
            cols[1].metric("AI Rec", item['ai_recommended'])
            
            default_override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
            override = cols[2].number_input(
                "Bake", value=default_override, min_value=0, max_value=500,
                key=f"bake_{item['item_id']}", label_visibility="collapsed"
            )
        
        if st.button("💾 Confirm Production Plan", type="primary", key="confirm_production"):
            for item in items:
                bake_val = st.session_state.get(f"bake_{item['item_id']}", item['ai_recommended'])
                conn.execute(
                    "UPDATE plan_items SET baker_override=?, actually_produced=? WHERE id=?",
                    (bake_val, bake_val, item['item_id'])
                )
            conn.commit()
            st.success("✅ Production plan confirmed! Now selling from POS...")
            st.balloons()
            st.rerun()
        
        st.markdown("---")
        
        # ---- EVENING: Auto-Calculated Waste + Tagging ----
        st.subheader("🌆 End of Day: Review Waste")
        st.caption("Sales are auto-tracked by POS. Split today's waste by reason.")
        
        today_str = today
        waste_items = []
        
        for item in items:
            produced = item['actually_produced'] if item['actually_produced'] else (item['baker_override'] if item['baker_override'] else item['ai_recommended'])
            
            # Auto-count sales from POS for today
            sold_today = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0) as total_sold
                FROM sales
                WHERE product_id = ? AND date(timestamp) = ?
            """, (item['product_id'], today_str)).fetchone()['total_sold']
            
            total_waste = max(0, produced - sold_today)
            
            st.markdown(f"#### {item['product']}")
            cols = st.columns([1, 1, 1])
            cols[0].metric("Produced", produced)
            cols[1].metric("Sold", sold_today)
            cols[2].metric("Total Waste", total_waste)
            
            if total_waste > 0:
                st.caption(f"Split the {total_waste} wasted units by reason:")
                
                reason_cols = st.columns(5)
                
                overproduction = reason_cols[0].number_input(
                    "Overproduction", min_value=0, max_value=total_waste, value=total_waste,
                    key=f"overprod_{item['item_id']}", label_visibility="visible"
                )
                kitchen = reason_cols[1].number_input(
                    "Kitchen accident", min_value=0, max_value=total_waste, value=0,
                    key=f"kitchen_{item['item_id']}", label_visibility="visible"
                )
                damaged = reason_cols[2].number_input(
                    "Damaged/dropped", min_value=0, max_value=total_waste, value=0,
                    key=f"damaged_{item['item_id']}", label_visibility="visible"
                )
                expired = reason_cols[3].number_input(
                    "Expired/stale", min_value=0, max_value=total_waste, value=0,
                    key=f"expired_{item['item_id']}", label_visibility="visible"
                )
                other = reason_cols[4].number_input(
                    "Other", min_value=0, max_value=total_waste, value=0,
                    key=f"other_{item['item_id']}", label_visibility="visible"
                )
                
                allocated = overproduction + kitchen + damaged + expired + other
                if allocated != total_waste:
                    st.warning(f"⚠️ Allocated ({allocated}) doesn't match total waste ({total_waste}). Please adjust.")
                
                # Store all waste entries
                waste_breakdown = [
                    ("overproduction", overproduction),
                    ("kitchen accident", kitchen),
                    ("damaged/dropped", damaged),
                    ("expired/stale", expired),
                    ("other", other),
                ]
                
                for reason, qty in waste_breakdown:
                    if qty > 0:
                        waste_items.append({
                            'item_id': item['item_id'],
                            'product_id': item['product_id'],
                            'product': item['product'],
                            'produced': produced,
                            'sold': sold_today,
                            'waste_qty': qty,
                            'reason': reason
                        })
            else:
                # No waste
                waste_items.append({
                    'item_id': item['item_id'],
                    'product_id': item['product_id'],
                    'product': item['product'],
                    'produced': produced,
                    'sold': sold_today,
                    'waste_qty': 0,
                    'reason': 'none'
                })
        
        if st.button("📋 Close Day & Log Waste", type="primary", key="close_day"):
            # Update plan_items with totals
            for item in items:
                # Sum all waste for this item
                item_waste_entries = [w for w in waste_items if w['item_id'] == item['item_id']]
                total_w = sum(w['waste_qty'] for w in item_waste_entries)
                total_s = item_waste_entries[0]['sold'] if item_waste_entries else 0
                
                # Find primary reason (the one with the most waste)
                primary_reason = "overproduction"
                max_qty = 0
                for w in item_waste_entries:
                    if w['waste_qty'] > max_qty:
                        max_qty = w['waste_qty']
                        primary_reason = w['reason']
                
                conn.execute(
                    "UPDATE plan_items SET actually_sold=?, wasted=?, waste_reason=? WHERE id=?",
                    (total_s, total_w, primary_reason, item['item_id'])
                )
            
            # Insert into waste_log
            for wi in waste_items:
                if wi['waste_qty'] > 0:
                    conn.execute(
                        "INSERT INTO waste_log (plan_item_id, store, product_id, date, quantity, reason, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (wi['item_id'], "Store", wi['product_id'], today_str, wi['waste_qty'], wi['reason'], '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                else:
                    # Log zero waste as "no waste"
                    conn.execute(
                        "INSERT INTO waste_log (plan_item_id, store, product_id, date, quantity, reason, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (wi['item_id'], "Store", wi['product_id'], today_str, 0, 'none', '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
            
            conn.commit()
            st.success("✅ Day closed! Waste logged by reason.")
            st.balloons()
            st.rerun()
        
        st.markdown("---")
        
        # ---- AI vs Baker Performance (uses only overproduction waste) ----
        st.subheader("📊 AI Performance")
        st.caption("Only 'overproduction' waste counts against the AI. Accidents and damage are excluded.")
        
        history = conn.execute("""
            SELECT pi.ai_recommended, pi.baker_override, pi.actually_sold, pi.wasted, pi.waste_reason, pp.date
            FROM plan_items pi
            JOIN production_plans pp ON pi.plan_id = pp.id
            WHERE pi.actually_sold IS NOT NULL
        """).fetchall()
        
        if history:
            ai_waste = 0
            baker_waste = 0
            
            for h in history:
                baked = h['baker_override'] if h['baker_override'] else h['ai_recommended']
                sold = h['actually_sold'] or 0
                reason = h['waste_reason'] or 'overproduction'
                
                # AI waste: what would have been wasted if they followed AI recommendation
                ai_w = max(0, h['ai_recommended'] - sold)
                
                # Baker waste: only count overproduction waste
                if reason == 'overproduction':
                    baker_w = h['wasted'] or 0
                else:
                    baker_w = 0  # Accidents don't count against the baker
                
                ai_waste += ai_w
                baker_waste += baker_w
            
            days = len(set(h['date'] for h in history))
            
            col1, col2 = st.columns(2)
            col1.metric("🤖 AI Estimated Waste", int(ai_waste), help="What AI would have wasted")
            col2.metric("👨‍🍳 Baker Waste (overproduction only)", int(baker_waste), help="Excludes accidents/damage")
            
            improvement = baker_waste - ai_waste
            if improvement > 0:
                st.success(f"✅ Over {days} days, AI reduced overproduction waste by **{int(improvement)} units**")
            elif improvement < 0:
                st.warning(f"⚠️ Baker better by {abs(int(improvement))} units")
            else:
                st.info("Equal.")
    
    else:
        st.info("Plan has no items.")
        if st.button("🔄 Retrain Models", key="retrain_items"):
            from engine import train_all_models, generate_forecast, save_forecast_to_db
            count = train_all_models()
            if count > 0:
                forecast = generate_forecast()
                save_forecast_to_db(forecast)
                st.rerun()

# ---- Sidebar ----
st.sidebar.subheader("📊 Quick Stats")
total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) as rev FROM sales").fetchone()['rev']
st.sidebar.metric("Total Sales", total_sales)
st.sidebar.metric("Total Revenue", f"${total_revenue:.2f}")

# Waste breakdown
total_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log").fetchone()[0]
overproduction_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason='overproduction'").fetchone()[0]
accident_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason!='overproduction'").fetchone()[0]
st.sidebar.metric("Total Waste", total_waste)
st.sidebar.metric("Overproduction", overproduction_waste)
st.sidebar.metric("Accidents/Other", accident_waste)

conn.close()