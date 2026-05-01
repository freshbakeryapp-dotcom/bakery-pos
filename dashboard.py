import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

# Migrate old schema
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN actually_produced INTEGER")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN waste_reason TEXT DEFAULT 'overproduction'")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN kitchen_accident INTEGER DEFAULT 0")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN damaged_dropped INTEGER DEFAULT 0")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN expired_stale INTEGER DEFAULT 0")
except:
    pass
try:
    conn.execute("ALTER TABLE plan_items ADD COLUMN other_loss INTEGER DEFAULT 0")
except:
    pass
try:
    conn.execute("SELECT actually_sold FROM plan_items LIMIT 1")
except:
    conn.execute("ALTER TABLE plan_items ADD COLUMN actually_sold INTEGER")

from db import init_db
init_db()

latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

# ============================================================
# MODE 1: NO FORECAST
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
    
    st.markdown("---")
    st.subheader("🚀 Import Historical CSV")
    csv_file = st.file_uploader("Upload POS CSV", type=["csv"], key="csv_import")
    
    if csv_file is not None:
        raw_df = pd.read_csv(csv_file)
        st.success(f"✅ {len(raw_df)} rows loaded")
        
        if st.button("📥 Import & Train AI", type="primary", key="do_import_v4"):
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
                    product_match = conn.execute("SELECT id FROM products WHERE LOWER(name) = LOWER(?)", (product_name,)).fetchone()
                    if not product_match:
                        conn.execute("INSERT INTO products (name, category, price) VALUES (?, ?, ?)", (product_name, "Imported", price))
                        product_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    else:
                        product_id = product_match['id']
                    conn.execute("INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)", (product_id, store, qty, price, qty * price, f"{date_val} 10:00:00"))
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
            # Weather for forecast date
    from src.weather import add_weather_to_forecast
    # Add a small weather indicator
    try:
        from src.weather import get_weather_for_period
        target_dates = pd.Series([pd.to_datetime(plan_date)])
        weather = get_weather_for_period(target_dates)
        if not weather.empty:
            rain = weather.iloc[0].get('precipitation_mm', 0)
            is_rainy = weather.iloc[0].get('is_rainy', False)
            if is_rainy:
                st.warning(f"🌧️ Rain forecast: {rain:.1f}mm — foot traffic may be affected")
    except:
        pass
    else:
        st.warning(f"⚠️ Plan for {plan_date}")
    
    items = conn.execute("""
        SELECT pi.id as item_id, pi.ai_recommended, pi.baker_override,
               pi.actually_produced, pi.kitchen_accident, pi.damaged_dropped,
               pi.expired_stale, pi.other_loss, pi.wasted, pi.waste_reason,
               pi.actually_sold, p.name as product, p.id as product_id
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
        ORDER BY p.name
    """, (latest_plan['id'],)).fetchall()
    
    if items:
        # Check if production has been confirmed
        production_confirmed = any(item['actually_produced'] is not None and item['actually_produced'] > 0 for item in items)
        day_closed = any(item['actually_sold'] is not None for item in items)
        
        # ============================================================
        # STEP 1: MORNING — Confirm Production Plan
        # ============================================================
        if not production_confirmed:
            st.subheader("🌅 Morning: Confirm Production Plan")
            st.caption("Override the AI with what you'll actually bake today.")
            
            for item in items:
                cols = st.columns([2, 1, 1])
                cols[0].write(f"**{item['product']}**")
                cols[1].metric("AI Rec", item['ai_recommended'])
                default_override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
                override = cols[2].number_input("Bake", value=default_override, min_value=0, max_value=500,
                    key=f"bake_{item['item_id']}", label_visibility="collapsed")
            
            if st.button("💾 Confirm Production Plan", type="primary", key="confirm_production"):
                for item in items:
                    bake_val = st.session_state.get(f"bake_{item['item_id']}", item['ai_recommended'])
                    conn.execute(
                        "UPDATE plan_items SET baker_override=?, actually_produced=? WHERE id=?",
                        (bake_val, bake_val, item['item_id'])
                    )
                conn.commit()
                st.success("✅ Production confirmed! Start selling in POS.")
                st.balloons()
                st.rerun()
        
        # ============================================================
        # STEP 2: EVENING — Log Non-Sales Losses
        # ============================================================
        elif production_confirmed and not day_closed:
            st.subheader("🌆 Evening Step 1: Log Non-Sales Losses")
            st.caption("Record accidents, damage, expired items, or other losses. Sales are tracked automatically by the POS.")
            
            today_str = today
            
            for item in items:
                produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                
                # Auto-count sales from POS
                sold_today = conn.execute("""
                    SELECT COALESCE(SUM(quantity), 0) as total_sold
                    FROM sales WHERE product_id = ? AND date(timestamp) = ?
                """, (item['product_id'], today_str)).fetchone()['total_sold']
                
                st.markdown(f"#### {item['product']}")
                cols = st.columns([1, 1, 1])
                cols[0].metric("Produced", produced)
                cols[1].metric("Sold (auto)", sold_today)
                cols[2].metric("Remaining", produced - sold_today)
                
                st.caption("Log any non-sales losses:")
                loss_cols = st.columns(4)
                
                kitchen = loss_cols[0].number_input("Kitchen accident", min_value=0, max_value=produced, value=0,
                    key=f"kitchen_{item['item_id']}", label_visibility="visible")
                damaged = loss_cols[1].number_input("Damaged/dropped", min_value=0, max_value=produced, value=0,
                    key=f"damaged_{item['item_id']}", label_visibility="visible")
                expired = loss_cols[2].number_input("Expired/stale", min_value=0, max_value=produced, value=0,
                    key=f"expired_{item['item_id']}", label_visibility="visible")
                other = loss_cols[3].number_input("Other", min_value=0, max_value=produced, value=0,
                    key=f"other_{item['item_id']}", label_visibility="visible")
            
            if st.button("📋 Close Day & Calculate Overproduction", type="primary", key="close_day"):
                for item in items:
                    produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                    sold_today = conn.execute("""
                        SELECT COALESCE(SUM(quantity), 0) as total_sold
                        FROM sales WHERE product_id = ? AND date(timestamp) = ?
                    """, (item['product_id'], today_str)).fetchone()['total_sold']
                    
                    kitchen_val = st.session_state.get(f"kitchen_{item['item_id']}", 0)
                    damaged_val = st.session_state.get(f"damaged_{item['item_id']}", 0)
                    expired_val = st.session_state.get(f"expired_{item['item_id']}", 0)
                    other_val = st.session_state.get(f"other_{item['item_id']}", 0)
                    
                    # Overproduction = Produced - Accidents - Damage - Expired - Other - Sales
                    overproduction = max(0, produced - kitchen_val - damaged_val - expired_val - other_val - sold_today)
                    
                    conn.execute("""
                        UPDATE plan_items 
                        SET actually_sold=?, kitchen_accident=?, damaged_dropped=?, expired_stale=?, other_loss=?,
                            wasted=?, waste_reason='overproduction'
                        WHERE id=?
                    """, (sold_today, kitchen_val, damaged_val, expired_val, other_val, overproduction, item['item_id']))
                    
                    # Log each loss type to waste_log
                    loss_types = [
                        ("kitchen accident", kitchen_val),
                        ("damaged/dropped", damaged_val),
                        ("expired/stale", expired_val),
                        ("other", other_val),
                        ("overproduction", overproduction),
                    ]
                    for reason, qty in loss_types:
                        if qty > 0 or reason == "overproduction":
                            conn.execute(
                                "INSERT INTO waste_log (plan_item_id, store, product_id, date, quantity, reason, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (item['item_id'], "Store", item['product_id'], today_str, qty, reason, '', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            )
                
                conn.commit()
                st.success("✅ Day closed! Overproduction calculated automatically.")
                st.balloons()
                st.rerun()
        
        # ============================================================
        # STEP 3: DAY CLOSED — Show Summary
        # ============================================================
        else:
            st.subheader("📊 Day Summary")
            st.caption(f"Day closed. Reviewing results for {plan_date}.")
            
            for item in items:
                produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                sold = item['actually_sold'] or 0
                kitchen = item['kitchen_accident'] or 0
                damaged = item['damaged_dropped'] or 0
                expired = item['expired_stale'] or 0
                other = item['other_loss'] or 0
                overproduction = item['wasted'] or 0

            # Stockout detection summary
            st.markdown("---")
            st.subheader("🔍 Stockout Detection")
            
            stockout_check = conn.execute("""
                SELECT pi.ai_recommended, pi.actually_produced, pi.actually_sold,
                       p.name as product
                FROM plan_items pi
                JOIN products p ON pi.product_id = p.id
                JOIN production_plans pp ON pi.plan_id = pp.id
                WHERE pi.actually_sold IS NOT NULL AND pp.date = ?
            """, (plan_date,)).fetchall()
            
            stockouts_today = []
            for sc in stockout_check:
                baked = sc['actually_produced'] or sc['ai_recommended']
                sold = sc['actually_sold'] or 0
                if sold >= baked and baked > 0:
                    stockouts_today.append(sc['product'])
            
            if stockouts_today:
                st.warning(f"⚠️ Possible stockouts today: {', '.join(stockouts_today)}. Sales matched or exceeded production — true demand may be higher. The model will correct for this in future forecasts.")
            else:
                st.success("✅ No stockouts detected today. Sales were below production.")
                
                st.markdown(f"#### {item['product']}")
                cols = st.columns(6)
                cols[0].metric("Produced", produced)
                cols[1].metric("Sold", sold)
                cols[2].metric("Kitchen", kitchen)
                cols[3].metric("Damaged", damaged)
                cols[4].metric("Expired", expired)
                cols[5].metric("Overproduction", overproduction)
            
            st.markdown("---")
            st.subheader("📊 AI vs Baker Performance")
            st.caption("Only overproduction waste counts against the AI forecast.")
            
            history = conn.execute("""
                SELECT pi.ai_recommended, pi.baker_override, pi.actually_sold, pi.wasted, pp.date
                FROM plan_items pi
                JOIN production_plans pp ON pi.plan_id = pp.id
                WHERE pi.actually_sold IS NOT NULL
            """).fetchall()
            
            if history:
                ai_waste = sum(max(0, h['ai_recommended'] - (h['actually_sold'] or 0)) for h in history)
                baker_waste = sum(h['wasted'] or 0 for h in history)
                days = len(set(h['date'] for h in history))
                
                col1, col2 = st.columns(2)
                col1.metric("🤖 AI Estimated Waste", int(ai_waste))
                col2.metric("👨‍🍳 Baker Overproduction", int(baker_waste))
                
                improvement = baker_waste - ai_waste
                if improvement > 0:
                    st.success(f"✅ Over {days} days, AI reduced overproduction by **{int(improvement)} units**")
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

total_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log").fetchone()[0]
overproduction_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason='overproduction'").fetchone()[0]
accident_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason!='overproduction' AND reason!='none'").fetchone()[0]
st.sidebar.metric("Total Waste", total_waste)
st.sidebar.metric("Overproduction", overproduction_waste)
st.sidebar.metric("Accidents/Other", accident_waste)

conn.close()