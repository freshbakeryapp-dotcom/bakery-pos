import streamlit as st
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

# ---- Store Filter ----
stores = conn.execute("SELECT DISTINCT store FROM sales ORDER BY store").fetchall()
store_list = [s['store'] for s in stores]
selected_store = st.selectbox("📍 Filter by Store", ["All Stores"] + store_list)

# ---- Latest Forecast ----
latest_plan = conn.execute("""
    SELECT * FROM production_plans 
    ORDER BY id DESC LIMIT 1
""").fetchone()

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
            pi.id as item_id,
            pi.ai_recommended,
            pi.baker_override,
            pi.actually_sold,
            pi.wasted,
            p.name as product,
            p.id as product_id
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
        cols[2].markdown("**Your Override**")
        cols[3].markdown("**Sold**")
        cols[4].markdown("**Wasted**")
        
        total_bake = 0
        total_sold = 0
        total_wasted = 0
        
        for item in items:
            cols = st.columns([2, 1, 1, 1, 1])
            cols[0].write(item['product'])
            cols[1].write(str(item['ai_recommended']))
            
            # Override input
            default_override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
            override = cols[2].number_input(
                "override",
                value=default_override,
                min_value=0,
                max_value=500,
                key=f"override_{item['item_id']}",
                label_visibility="collapsed"
            )
            
            # Sold input (waste logging)
            sold_default = item['actually_sold'] if item['actually_sold'] else override
            sold = cols[3].number_input(
                "sold",
                value=sold_default,
                min_value=0,
                max_value=override,
                key=f"sold_{item['item_id']}",
                label_visibility="collapsed"
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
        
        # Save overrides AND waste log
        if st.button("💾 Save Overrides & Log Waste", type="primary"):
            for item in items:
                override_key = f"override_{item['item_id']}"
                sold_key = f"sold_{item['item_id']}"
                
                override_val = st.session_state.get(override_key, item['ai_recommended'])
                sold_val = st.session_state.get(sold_key, override_val)
                wasted_val = override_val - sold_val
                
                conn.execute("""
                    UPDATE plan_items 
                    SET baker_override = ?, actually_sold = ?, wasted = ?
                    WHERE id = ?
                """, (override_val, sold_val, wasted_val, item['item_id']))
            
            conn.commit()
            st.success("✅ Overrides and waste logged!")
            st.balloons()
            st.rerun()
        
        # ---- AI vs Baker Comparison ----
        st.markdown("---")
        st.subheader("📊 AI vs Baker Performance")
        
        # All historical data
        history = conn.execute("""
            SELECT 
                pi.ai_recommended,
                pi.baker_override,
                pi.actually_sold,
                pi.wasted,
                pp.date
            FROM plan_items pi
            JOIN production_plans pp ON pi.plan_id = pp.id
            WHERE pi.actually_sold IS NOT NULL
            ORDER BY pp.date DESC
        """).fetchall()
        
        if history:
            total_ai_waste = 0
            total_baker_waste = 0
            total_days = len(set(h['date'] for h in history))
            
            for h in history:
                baked = h['baker_override'] if h['baker_override'] else h['ai_recommended']
                sold = h['actually_sold'] if h['actually_sold'] else 0
                ai_waste = max(0, h['ai_recommended'] - sold)
                baker_waste = h['wasted'] if h['wasted'] else 0
                total_ai_waste += ai_waste
                total_baker_waste += baker_waste
            
            col1, col2 = st.columns(2)
            col1.metric("🤖 AI Estimated Waste", int(total_ai_waste))
            col2.metric("👨‍🍳 Baker Actual Waste", int(total_baker_waste))
            
            improvement = total_baker_waste - total_ai_waste
            if improvement > 0:
                st.success(f"✅ Over {total_days} day(s), AI would have reduced waste by **{int(improvement)} units**")
            elif improvement < 0:
                st.warning(f"⚠️ Baker performed better by {abs(int(improvement))} units")
            else:
                st.info("AI and baker performed equally.")
        else:
            st.info("Log waste above to see AI vs Baker comparison.")
    
    else:
        st.info("No plan items found. Click 'Retrain Models Now' below.")
else:
    st.warning("No forecast yet. Make sales in POS, then click below.")
    if st.button("🔄 Retrain Models Now"):
        from engine import train_all_models, generate_forecast, save_forecast_to_db
        with st.spinner("Training models from all sales data..."):
            count = train_all_models()
            if count > 0:
                st.success(f"Trained {count} models!")
                forecast = generate_forecast()
                save_forecast_to_db(forecast)
                st.success("Forecast generated!")
                st.rerun()
            else:
                st.error("Need more sales data to train models.")

# ---- Manual Retrain Button (always available) ----
st.markdown("---")
with st.expander("⚙️ Advanced: Manual Retrain"):
    if st.button("🔄 Retrain Models Now"):
        from engine import train_all_models, generate_forecast, save_forecast_to_db
        with st.spinner("Training..."):
            count = train_all_models()
            if count > 0:
                st.success(f"Trained {count} models")
                forecast = generate_forecast()
                save_forecast_to_db(forecast)
                st.rerun()
            else:
                st.error("Need more sales data.")

# ---- Sidebar Stats ----
st.sidebar.subheader("📊 Quick Stats")
total_sales = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()['cnt']
total_revenue = conn.execute("SELECT COALESCE(SUM(total), 0) as rev FROM sales").fetchone()['rev']
total_products = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()['cnt']
st.sidebar.metric("Total Sales", total_sales)
st.sidebar.metric("Total Revenue", f"${total_revenue:.2f}")
st.sidebar.metric("Products", total_products)

conn.close()