import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

if not latest_plan:
    st.warning("⚠️ No forecast yet.")
    
    date_count = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
    total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
    
    st.write(f"📅 Unique sale dates: **{date_count}** (need 3+)")
    st.write(f"📦 Total sales rows: **{total_sales}**")
    
    # Show a few sample dates
    sample_dates = conn.execute("SELECT DISTINCT date(timestamp) as d FROM sales LIMIT 5").fetchall()
    if sample_dates:
        st.write("Sample dates in DB:")
        for d in sample_dates:
            st.write(f"  - {d['d']}")
    
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
        # DEBUG: Check sales dates
    date_check = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
    sample = conn.execute("SELECT DISTINCT date(timestamp) as d FROM sales ORDER BY d LIMIT 5").fetchall()
    st.write(f"Unique dates: {date_check}")
    st.write("Sample:", [s['d'] for s in sample])
    st.markdown("---")
    st.subheader("🚀 Import Historical CSV")
    st.write("Upload your POS sales history CSV.")
    
    csv_file = st.file_uploader("Upload POS CSV", type=["csv"], key="csv_import")
    
    if csv_file is not None:
        raw_df = pd.read_csv(csv_file)
        st.success(f"✅ {len(raw_df)} rows loaded")
        st.write("Columns found:", list(raw_df.columns))
        st.dataframe(raw_df.head(3))
        
        if st.button("📥 Import & Train AI", type="primary", key="do_import"):
            inserted = 0
            with st.spinner("Importing..."):
                for _, row in raw_df.iterrows():
                    product_name = str(row.get('product', '')).strip()
                    product_match = conn.execute(
                        "SELECT id, price FROM products WHERE LOWER(name) = LOWER(?)",
                        (product_name,)
                    ).fetchone()
                    
                    if not product_match:
                        continue
                    
                    store = str(row.get('store', 'Gadong')).strip()
                    qty = int(row.get('quantity_sold', row.get('qty', 1)))
                    price = float(row.get('unit_price', row.get('price', product_match['price'])))
                    date_raw = str(row['date']).strip()
                    
                    # Normalize date to YYYY-MM-DD
                    try:
                        date_val = pd.to_datetime(date_raw).strftime("%Y-%m-%d")
                    except:
                        st.warning(f"Skipping row with bad date: {date_raw}")
                        continue
                    
                    timestamp = f"{date_val} 10:00:00"
                    
                    conn.execute(
                        "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (product_match['id'], store, qty, price, qty * price, timestamp)
                    )
                    inserted += 1
            
            conn.commit()
            st.success(f"✅ Imported {inserted} rows!")
            
            from engine import train_all_models, generate_forecast, save_forecast_to_db
            with st.spinner("Training AI..."):
                count = train_all_models()
                if count > 0:
                    forecast = generate_forecast()
                    save_forecast_to_db(forecast)
                    st.success(f"🎉 {count} models trained!")
                    st.balloons()
                    st.rerun()
                else:
                    date_count_after = conn.execute("SELECT COUNT(DISTINCT date(timestamp)) as cnt FROM sales").fetchone()['cnt']
                    st.error(f"Still only {date_count_after} unique dates after import. Need at least 3.")

else:
    plan_date = latest_plan['date']
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if plan_date == today:
        st.success(f"✅ Today's Plan — {plan_date}")
    elif plan_date == tomorrow:
        st.info(f"📋 Tomorrow's Plan — {plan_date}")
    else:
        st.warning(f"⚠️ Latest plan is for {plan_date}")
    
    items = conn.execute("""
        SELECT pi.id as item_id, pi.ai_recommended, pi.baker_override,
               pi.actually_sold, pi.wasted, p.name as product
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
        ORDER BY p.name
    """, (latest_plan['id'],)).fetchall()
    
    if items:
        st.subheader("📋 Production Plan")
        
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].markdown("**Product**")
        cols[1].markdown("**AI Rec**")
        cols[2].markdown("**Override**")
        cols[3].markdown("**Sold**")
        cols[4].markdown("**Wasted**")
        
        for item in items:
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].write(item['product'])
            cols[1].write(str(item['ai_recommended']))
            
            default_override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
            override = cols[2].number_input("ov", value=default_override, min_value=0, max_value=500,
                key=f"ov_{item['item_id']}", label_visibility="collapsed")
            
            sold_default = item['actually_sold'] if item['actually_sold'] else override
            sold = cols[3].number_input("sl", value=sold_default, min_value=0, max_value=override,
                key=f"sl_{item['item_id']}", label_visibility="collapsed")
            
            wasted = override - sold
            cols[4].markdown(f"**{wasted}**")
        
        st.markdown("---")
        if st.button("💾 Save Overrides & Log Waste", type="primary", key="save_plan"):
            for item in items:
                ov_val = st.session_state.get(f"ov_{item['item_id']}", item['ai_recommended'])
                sl_val = st.session_state.get(f"sl_{item['item_id']}", ov_val)
                w_val = ov_val - sl_val
                conn.execute(
                    "UPDATE plan_items SET baker_override=?, actually_sold=?, wasted=? WHERE id=?",
                    (ov_val, sl_val, w_val, item['item_id'])
                )
            conn.commit()
            st.success("✅ Saved!")
            st.balloons()
            st.rerun()
        
        st.markdown("---")
        st.subheader("📊 AI vs Baker")
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
            col1.metric("🤖 AI Waste", int(ai_waste))
            col2.metric("👨‍🍳 Baker Waste", int(baker_waste))
            imp = baker_waste - ai_waste
            if imp > 0:
                st.success(f"✅ Over {days} days, AI reduced waste by **{int(imp)} units**")
            elif imp < 0:
                st.warning(f"⚠️ Baker better by {abs(int(imp))} units")
            else:
                st.info("Equal.")
        else:
            st.info("Log waste to see comparison.")
    else:
        st.info("Plan has no items. Try retraining.")
        if st.button("🔄 Retrain Models", key="retrain_items"):
            from engine import train_all_models, generate_forecast, save_forecast_to_db
            count = train_all_models()
            if count > 0:
                forecast = generate_forecast()
                save_forecast_to_db(forecast)
                st.rerun()

st.sidebar.subheader("📊 Quick Stats")
total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) as rev FROM sales").fetchone()['rev']
st.sidebar.metric("Total Sales", total_sales)
st.sidebar.metric("Total Revenue", f"${total_revenue:.2f}")
st.sidebar.metric("Plans", conn.execute("SELECT COUNT(*) as cnt FROM production_plans").fetchone()['cnt'])

conn.close()