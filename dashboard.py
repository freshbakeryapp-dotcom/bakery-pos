import streamlit as st
import sqlite3
from datetime import datetime, timedelta
from engine import train_all_models, generate_forecast, save_forecast_to_db

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

# Train models on demand
if st.button("🔄 Retrain Models & Generate Forecast", type="primary"):
    with st.spinner("Training models from all sales data..."):
        count = train_all_models()
        if count > 0:
            st.success(f"Trained {count} product-store models")
            forecast = generate_forecast()
            if forecast:
                save_forecast_to_db(forecast)
                st.success(f"Forecast saved for tomorrow: {(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')}")
            else:
                st.warning("No forecast generated. Need more sales data.")
        else:
            st.warning("Not enough data to train models. Make some sales first.")

st.markdown("---")

# Show latest forecast
conn = sqlite3.connect("bakery.db")
latest_plan = conn.execute(
    "SELECT * FROM production_plans ORDER BY id DESC LIMIT 1"
).fetchone()

if latest_plan:
    st.subheader(f"📋 Production Plan for {latest_plan['date']}")
    
    items = conn.execute("""
        SELECT 
            pi.ai_recommended,
            pi.baker_override,
            pi.actually_sold,
            pi.wasted,
            p.name as product,
            pp.store
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        JOIN production_plans pp ON pi.plan_id = pp.id
        WHERE pi.plan_id = ?
    """, (latest_plan['id'],)).fetchall()
    
    if items:
        for item in items:
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(item['product'])
            cols[1].metric("AI Rec", item['ai_recommended'])
            override = item['baker_override'] if item['baker_override'] else item['ai_recommended']
            cols[2].metric("Baked", override)
            cols[3].metric("Wasted", item['wasted'] if item['wasted'] else 0)
    else:
        st.info("No plan items found.")
else:
    st.info("No forecast generated yet. Click the button above to train models and generate your first forecast.")

conn.close()