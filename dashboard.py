import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

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
        st.caption("Sales are tracked automatically by the POS. Waste = Produced - Sold.")
        
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
            
            waste = max(0, produced - sold_today)
            
            cols = st.columns([2, 1, 1, 1, 2])
            cols[0].write(f"**{item['product']}**")
            cols[1].metric("Produced", produced)
            cols[2].metric("Sold", sold_today)
            cols[3].metric("Waste", waste)
            
            # Waste reason dropdown
            reason = cols[4].selectbox(
                "Reason",
                ["overproduction", "kitchen accident", "damaged/dropped", "expired/stale", "other"],
                key=f"reason_{item['item_id']}",
                label_visibility="collapsed"
            )
            
            waste_items.append({
                'item_id': item['item_id'],
                'product_id': item['product_id'],
                'product': item['product'],
                'produced': produced,
                'sold': sold_today,
                'waste': waste,
                'reason': reason
            })
        
        if st.button("📋 Close Day & Log Waste", type="primary", key="close_day"):
            for wi in waste_items:
                # Update plan_item
                conn.execute(
                    "UPDATE plan_items SET actually_sold=?, wasted=?, waste_reason=? WHERE id=?",
                    (wi['sold'], wi['waste'], wi['reason'], wi['item_id'])
                )
                # Log to waste_log
                conn.execute(
                    "INSERT INTO waste_log (plan_item_id, store, product_id, date, quantity, reason, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (wi['item_id'], "Store", wi['product_id'], today_str, wi['waste'], wi['reason'], '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
            conn.commit()
            st.success("✅ Day closed! Waste logged.")
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