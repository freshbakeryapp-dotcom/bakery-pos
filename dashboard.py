import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

# Migrate old schema
for col, col_type in [
    ("actually_produced", "INTEGER"),
    ("waste_reason", "TEXT DEFAULT 'overproduction'"),
    ("kitchen_accident", "INTEGER DEFAULT 0"),
    ("damaged_dropped", "INTEGER DEFAULT 0"),
    ("expired_stale", "INTEGER DEFAULT 0"),
    ("other_loss", "INTEGER DEFAULT 0"),
    ("actually_sold", "INTEGER"),
    ("p90_safe", "INTEGER DEFAULT 0"),
]:
    try:
        conn.execute(f"ALTER TABLE plan_items ADD COLUMN {col} {col_type}")
    except:
        pass

from db import init_db
init_db()

# Auto-train check
last_train_time = conn.execute("SELECT MAX(created_at) as last_time FROM production_plans").fetchone()['last_time']
should_auto_train = False
if last_train_time:
    last_train_dt = datetime.strptime(last_train_time, "%Y-%m-%d %H:%M:%S")
    hours_since_train = (datetime.now() - last_train_dt).total_seconds() / 3600
    if hours_since_train > 20:
        should_auto_train = True
    st.sidebar.write(f"Hours since last train: {hours_since_train:.1f}")
else:
    should_auto_train = True
    st.sidebar.write("No training history yet")

if should_auto_train:
    date_count = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
    if date_count >= 3:
        from engine import train_all_models, generate_forecast, save_forecast_to_db
        count = train_all_models()
        if count > 0:
            forecast = generate_forecast()
            save_forecast_to_db(forecast)
            st.sidebar.success(f"🔄 Auto-trained {count} models")

st.sidebar.markdown("---")
if last_train_time:
    st.sidebar.caption(f"🕐 Last trained: {last_train_time}")
else:
    st.sidebar.caption("🕐 Never trained")

latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

st.markdown("---")
if st.button("🔄 Retrain Models Now", key="retrain_global", type="secondary"):
    from engine import train_all_models, generate_forecast, save_forecast_to_db
    with st.spinner("Training..."):
        count = train_all_models()
        if count > 0:
            forecast = generate_forecast()
            save_forecast_to_db(forecast)
            st.success(f"✅ Trained {count} models!")
            st.rerun()
        else:
            st.error("Not enough data.")

if not latest_plan:
    st.warning("⚠️ No forecast yet.")
    date_count = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
    total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
    st.write(f"📅 Unique sale dates: **{date_count}** (need 3+)")
    st.write(f"📦 Total sales rows: **{total_sales}**")
    
    st.markdown("---")
    st.subheader("🚀 Import Historical CSV")
    csv_file = st.file_uploader("Upload POS CSV", type=["csv"], key="csv_import")
    
    if csv_file is not None:
        raw_df = pd.read_csv(csv_file)
        st.success(f"✅ {len(raw_df)} rows loaded")
        if st.button("📥 Import & Train AI", type="primary"):
            inserted = 0
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
                count = train_all_models()
                if count > 0:
                    forecast = generate_forecast()
                    save_forecast_to_db(forecast)
                    st.success(f"🎉 {count} models trained!")
                    st.balloons()
                    st.rerun()

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
        SELECT pi.id as item_id, pi.ai_recommended, pi.p90_safe, pi.baker_override,
               pi.actually_produced, pi.kitchen_accident, pi.damaged_dropped,
               pi.expired_stale, pi.other_loss, pi.wasted, pi.waste_reason,
               pi.actually_sold, p.name as product, p.id as product_id
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
        ORDER BY p.name
    """, (latest_plan['id'],)).fetchall()
    
    if items:
        production_confirmed = any(item['actually_produced'] is not None and item['actually_produced'] > 0 for item in items)
        day_closed = any(item['actually_sold'] is not None for item in items)
        
        if not production_confirmed:
            st.subheader("🌅 Morning: Confirm Production Plan")
            for item in items:
                cols = st.columns([2, 1, 1])
                cols[0].write(f"**{item['product']}**")
                ai_rec = item['ai_recommended']
                p90 = item['p90_safe'] or ai_rec
                cols[1].metric("AI Rec", ai_rec)
                if p90 > ai_rec:
                    cols[1].caption(f"🛡️ Safe: {p90}")
                default_override = item['baker_override'] if item['baker_override'] else ai_rec
                override = cols[2].number_input("Bake", value=default_override, min_value=0, max_value=500,
                    key=f"bake_{item['item_id']}", label_visibility="collapsed")
            if st.button("💾 Confirm Production Plan", type="primary"):
                for item in items:
                    bake_val = st.session_state.get(f"bake_{item['item_id']}", item['ai_recommended'])
                    conn.execute("UPDATE plan_items SET baker_override=?, actually_produced=? WHERE id=?", (bake_val, bake_val, item['item_id']))
                conn.commit()
                st.success("✅ Production confirmed!")
                st.balloons()
                st.rerun()
        
        elif production_confirmed and not day_closed:
            st.subheader("🌆 Evening: Log Non-Sales Losses")
            today_str = today
            for item in items:
                produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                sold_today = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM sales WHERE product_id = ? AND date(timestamp) = ?", (item['product_id'], today_str)).fetchone()[0]
                st.markdown(f"#### {item['product']}")
                cols = st.columns([1,1,1])
                cols[0].metric("Produced", produced)
                cols[1].metric("Sold", sold_today)
                cols[2].metric("Remaining", produced - sold_today)
                loss_cols = st.columns(4)
                kitchen = loss_cols[0].number_input("Kitchen", min_value=0, max_value=produced, value=0, key=f"k_{item['item_id']}", label_visibility="visible")
                damaged = loss_cols[1].number_input("Damaged", min_value=0, max_value=produced, value=0, key=f"d_{item['item_id']}", label_visibility="visible")
                expired = loss_cols[2].number_input("Expired", min_value=0, max_value=produced, value=0, key=f"e_{item['item_id']}", label_visibility="visible")
                other = loss_cols[3].number_input("Other", min_value=0, max_value=produced, value=0, key=f"ot_{item['item_id']}", label_visibility="visible")
            if st.button("📋 Close Day", type="primary"):
                for item in items:
                    produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                    sold_today = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM sales WHERE product_id = ? AND date(timestamp) = ?", (item['product_id'], today_str)).fetchone()[0]
                    kv = st.session_state.get(f"k_{item['item_id']}", 0)
                    dv = st.session_state.get(f"d_{item['item_id']}", 0)
                    ev = st.session_state.get(f"e_{item['item_id']}", 0)
                    ov = st.session_state.get(f"ot_{item['item_id']}", 0)
                    overproduction = max(0, produced - kv - dv - ev - ov - sold_today)
                    conn.execute("UPDATE plan_items SET actually_sold=?, kitchen_accident=?, damaged_dropped=?, expired_stale=?, other_loss=?, wasted=?, waste_reason='overproduction' WHERE id=?", (sold_today, kv, dv, ev, ov, overproduction, item['item_id']))
                    for reason, qty in [("kitchen accident", kv), ("damaged/dropped", dv), ("expired/stale", ev), ("other", ov), ("overproduction", overproduction)]:
                        if qty > 0 or reason == "overproduction":
                            conn.execute("INSERT INTO waste_log (plan_item_id, store, product_id, date, quantity, reason, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (item['item_id'], "Store", item['product_id'], today_str, qty, reason, '', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("✅ Day closed!")
                st.balloons()
                st.rerun()
        
        else:
            st.subheader("📊 Day Summary")
            for item in items:
                produced = item['actually_produced'] or (item['baker_override'] or item['ai_recommended'])
                sold = item['actually_sold'] or 0
                p90 = item['p90_safe'] or item['ai_recommended']
                st.markdown(f"#### {item['product']}")
                cols = st.columns(7)
                cols[0].metric("AI Rec", item['ai_recommended'])
                cols[1].metric("P90 Safe", p90)
                cols[2].metric("Produced", produced)
                cols[3].metric("Sold", sold)
                cols[4].metric("Kitchen", item['kitchen_accident'] or 0)
                cols[5].metric("Damaged", item['damaged_dropped'] or 0)
                cols[6].metric("Overprod", item['wasted'] or 0)
            
            st.markdown("---")
            st.subheader("📊 AI vs Baker")
            history = conn.execute("SELECT pi.ai_recommended, pi.baker_override, pi.actually_sold, pi.wasted, pp.date FROM plan_items pi JOIN production_plans pp ON pi.plan_id = pp.id WHERE pi.actually_sold IS NOT NULL").fetchall()
            if history:
                ai_waste = sum(max(0, h['ai_recommended'] - (h['actually_sold'] or 0)) for h in history)
                baker_waste = sum(h['wasted'] or 0 for h in history)
                days = len(set(h['date'] for h in history))
                col1, col2 = st.columns(2)
                col1.metric("🤖 AI Waste", int(ai_waste))
                col2.metric("👨‍🍳 Baker Waste", int(baker_waste))
                imp = baker_waste - ai_waste
                if imp > 0:
                    st.success(f"✅ Over {days} days, AI reduced waste by **{int(imp)} units**")
                elif imp < 0:
                    st.warning(f"⚠️ Baker better by {abs(int(imp))} units")
                else:
                    st.info("Equal.")

# Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Quick Stats")
total_sales = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) FROM sales").fetchone()[0]
st.sidebar.metric("Total Sales", total_sales)
st.sidebar.metric("Total Revenue", f"${total_revenue:.2f}")
total_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log").fetchone()[0]
op_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason='overproduction'").fetchone()[0]
acc_waste = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM waste_log WHERE reason!='overproduction' AND reason!='none'").fetchone()[0]
st.sidebar.metric("Total Waste", total_waste)
st.sidebar.metric("Overproduction", op_waste)
st.sidebar.metric("Accidents/Other", acc_waste)

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Events")
from src.events import get_upcoming_events, add_event
upcoming = get_upcoming_events(7)
if upcoming:
    for ev in upcoming[:5]:
        emoji = {"low":"🟢","medium":"🟡","high":"🔴"}.get(ev['expected_impact'],"🟡")
        d = ev['description'] or ''
        st.sidebar.caption(f"{emoji} {ev['date']}: {ev['event_type'].replace('_',' ').title()} - {d[:20]}")
ev_date = st.sidebar.date_input("Date", key="ev_date")
ev_type = st.sidebar.selectbox("Type", ["nearby_event","construction","school_activity","promotion","holiday_local","other"], key="ev_type")
ev_impact = st.sidebar.selectbox("Impact", ["low","medium","high"], key="ev_impact")
ev_desc = st.sidebar.text_input("Description", key="ev_desc")
if st.sidebar.button("➕ Add Event"):
    add_event("Store", ev_date.strftime("%Y-%m-%d"), ev_type, ev_desc, ev_impact)
    st.sidebar.success("Added!")
    st.rerun()

conn.close()