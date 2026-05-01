import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

# ---- Store Filter ----
stores = conn.execute("SELECT DISTINCT store FROM sales ORDER BY store").fetchall()
store_list = [s['store'] for s in stores]
selected_store = st.selectbox("📍 Filter by Store", ["All Stores"] + store_list)

# ---- Latest Forecast ----
latest_plan = conn.execute("SELECT * FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()

if latest_plan:
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
        SELECT 
            pi.id as item_id, pi.ai_recommended, pi.baker_override,
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
        
        total_bake = 0
        total_sold = 0
        total_wasted = 0
        
        for item in items:
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].write(item['product'])
            cols[1].write(str(item['ai_recommended']))
            
            default_override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
            override = cols[2].number_input(
                "override", value=default_override, min_value=0, max_value=500,
                key=f"ov_{item['item_id']}", label_visibility="collapsed"
            )
            
            sold_default = item['actually_sold'] if item['actually_sold'] else override
            sold = cols[3].number_input(
                "sold", value=sold_default, min_value=0, max_value=override,
                key=f"sl_{item['item_id']}", label_visibility="collapsed"
            )
            
            wasted = override - sold
            cols[4].markdown(f"**{wasted}**")
            
            total_bake += override
            total_sold += sold
            total_wasted += wasted
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Baked", total_bake)
        col2.metric("Total Sold", total_sold)
        col3.metric("Total Wasted", total_wasted)
        
        if st.button("💾 Save Overrides & Log Waste", type="primary"):
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
        
        # AI vs Baker comparison
        st.markdown("---")
        st.subheader("📊 AI vs Baker Performance")
        
        history = conn.execute("""
            SELECT pi.ai_recommended, pi.baker_override, pi.actually_sold, pi.wasted, pp.date
            FROM plan_items pi
            JOIN production_plans pp ON pi.plan_id = pp.id
            WHERE pi.actually_sold IS NOT NULL
            ORDER BY pp.date DESC
        """).fetchall()
        
        if history:
            ai_waste_total = sum(max(0, h['ai_recommended'] - (h['actually_sold'] or 0)) for h in history)
            baker_waste_total = sum(h['wasted'] or 0 for h in history)
            days = len(set(h['date'] for h in history))
            
            col1, col2 = st.columns(2)
            col1.metric("🤖 AI Estimated Waste", int(ai_waste_total))
            col2.metric("👨‍🍳 Baker Actual Waste", int(baker_waste_total))
            
            improvement = baker_waste_total - ai_waste_total
            if improvement > 0:
                st.success(f"✅ Over {days} day(s), AI would have reduced waste by **{int(improvement)} units**")
            elif improvement < 0:
                st.warning(f"⚠️ Baker performed better by {abs(int(improvement))} units")
            else:
                st.info("AI and baker performed equally.")
        else:
            st.info("Log waste above to see AI vs Baker comparison.")

else:
    # No forecast exists
    st.warning("No forecast yet.")
    # If we just trained models, reload to show forecast
    if st.session_state.get('force_reload'):
        st.session_state.force_reload = False
        st.rerun()
    
    # ---- CSV Jumpstart ----
    st.markdown("---")
    st.subheader("🚀 Jumpstart Your AI")
    st.write("Upload your historical POS CSV to train the AI instantly.")
    
    csv_file = st.file_uploader("Upload Historical POS CSV", type=["csv"], key="historical_csv")
    
    if csv_file is not None:
        raw_df = pd.read_csv(csv_file)
        
        # Store in session state so it survives reruns
        st.session_state.raw_csv = raw_df
        
        st.success(f"✅ {len(raw_df)} rows detected")
        st.write("Preview:")
        st.dataframe(raw_df.head(5))

# Process the import if data is stored
if 'raw_csv' in st.session_state and st.session_state.raw_csv is not None:
    if st.button("📥 Import Historical Data & Train AI", type="primary", key="import_btn"):
        raw_df = st.session_state.raw_csv
        inserted = 0
        
        with st.spinner("Importing sales data..."):
            for _, row in raw_df.iterrows():
                product_name = str(row.get('product', '')).strip()
                product_match = conn.execute(
                    "SELECT id, price FROM products WHERE LOWER(name) = LOWER(?)",
                    (product_name,)
                ).fetchone()
                
                if product_match:
                    store = str(row.get('store', 'Gadong')).strip()
                    qty = int(row.get('quantity_sold', row.get('qty', row.get('quantity', 1))))
                    price = float(row.get('unit_price', row.get('price', product_match['price'])))
                    date_val = str(row['date']).strip()
                    
                    conn.execute(
                        "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (product_match['id'], store, qty, price, qty * price, f"{date_val} 10:00:00")
                    )
                    inserted += 1
        
        conn.commit()
        st.success(f"✅ Imported {inserted} sales records!")
        
        from engine import train_all_models, generate_forecast, save_forecast_to_db
        with st.spinner("Training AI on historical data..."):
            count = train_all_models()
            if count > 0:
                forecast = generate_forecast()
                save_forecast_to_db(forecast)
                st.success(f"🎉 AI trained on {count} models! Forecast ready.")
                st.balloons()
                st.session_state.raw_csv = None
                st.session_state.force_reload = True
                st.rerun()
            else:
                st.warning("Need more date variety. Upload a CSV with at least 3 different dates per product.")

# ---- Always-available Retrain Button ----
st.markdown("---")
if st.button("🔄 Retrain Models Now", key="retrain_bottom"):
    from engine import train_all_models, generate_forecast, save_forecast_to_db
    with st.spinner("Training..."):
        count = train_all_models()
        if count > 0:
            forecast = generate_forecast()
            save_forecast_to_db(forecast)
            st.success(f"✅ Trained {count} models! Forecast generated.")
            st.rerun()
        else:
            st.error("Need more sales data. Import historical CSV or make more POS sales across different dates.")

# Sidebar
st.sidebar.subheader("📊 Quick Stats")
total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) as rev FROM sales").fetchone()['rev']
st.sidebar.metric("Total Sales", total_sales)
st.sidebar.metric("Total Revenue", f"${total_revenue:.2f}")

conn.close()