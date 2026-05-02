import streamlit as st
from utils.ordering import get_order_recommendations, confirm_order
from db import get_db

st.set_page_config(page_title="Smart Ordering - Artisan Crumb", layout="wide")

st.markdown('<h1 style="font-family: \'Playfair Display\', serif;"> Smart Reorder</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #6B5444;">AI-calculated orders based on production plans + actual usage variance.</p>', unsafe_allow_html=True)

# Simulation Helper (Only if no data exists)
conn = get_db()
plans_count = conn.execute("SELECT count(*) FROM production_plans").fetchone()[0]
conn.close()

if plans_count == 0:
    st.warning("⚠️ No production plans found for the next 7 days.")
    if st.button("🧪 Simulate Next Week's Production (Demo)", type="secondary"):
        conn = get_db()
        # Inject dummy plans for the next 7 days
        prod_id = conn.execute("SELECT id FROM products LIMIT 1").fetchone()
        if prod_id:
            conn.executemany("""
                INSERT INTO production_plans (product_id, quantity, scheduled_date)
                VALUES (?, ?, date('now', '+' || ? || ' days'))
            """, [(prod_id["id"], 20, i) for i in range(1, 8)])
            conn.commit()
            st.success("✅ Simulated 20 units/day for next 7 days.")
            st.rerun()
        conn.close()
    st.stop()

# Main Logic
recs = get_order_recommendations(days_ahead=7)

if not recs:
    st.success("✅ Stock levels are healthy! No orders needed right now.")
    st.stop()

# Display Recommendations
st.subheader("📋 Recommended Orders")

total_cost = 0

for rec in recs:
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        
        with col1:
            st.markdown(f"### {rec['name']}")
            st.caption(f"Current Stock: {rec['current_stock']} {rec['unit']}")
            st.caption(f"Forecast Demand: {rec['forecast_demand']} units (Next 7 Days)")
            
        with col2:
            st.metric("Variance", f"{int((rec['variance_coeff']-1)*100)}%")
            st.caption(f"Confidence: {rec['confidence']}%")
            
        with col3:
            st.metric("Need", f"{rec['recommended_order']} {rec['unit']}")
            
        with col4:
            st.metric("Cost", f"${rec['estimated_cost']}")
            
        with col5:
            if st.button("✅ Confirm", key=f"btn_{rec['id']}", type="primary", use_container_width=True):
                confirm_order(rec['id'], rec['recommended_order'], rec['estimated_cost'])
                st.success(f"Order placed for {rec['name']}!")
                st.rerun()
        
        total_cost += rec['estimated_cost']

st.markdown("---")
st.info(f" **Total Estimated Spend: ${total_cost:.2f}**")