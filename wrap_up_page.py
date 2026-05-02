import streamlit as st
from utils.waste import get_wrap_up_data, log_waste, get_ai_waste_insights
from datetime import datetime

st.set_page_config(page_title="End of Day Wrap-Up", layout="wide")

st.markdown(f'<h1 style="font-family: \'Playfair Display\', serif;">🌙 End of Day Wrap-Up</h1>', unsafe_allow_html=True)
st.markdown('<p style="color: #6B5444;">Log waste to train AI. Every tap makes tomorrow\'s forecast smarter.</p>', unsafe_allow_html=True)

# Feedback message
if 'waste_logged' in st.session_state:
    st.success(st.session_state.waste_logged)
    del st.session_state.waste_logged

wrap_data = get_wrap_up_data()

if not wrap_data:
    st.info(" No production logged for today. Bake first, then wrap up.")
    st.stop()

st.subheader("📦 What happened to leftovers?")

for item in wrap_data:
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            st.markdown(f"### {item['product_name']}")
            st.caption(f"Made: {item['produced']} | Sold: {item['sold']}")
            
        with col2:
            remaining = item["remaining"]
            if remaining <= 0:
                st.markdown("✅ All accounted for")
            else:
                st.markdown(f"⚠️ **{remaining} left to log**")
                
        with col3:
            if remaining > 0:
                reason_col, qty_col, btn_col = st.columns([2, 1, 1])
                
                with reason_col:
                    reason = st.selectbox("Reason", 
                        ["Expired/Stale", "Kitchen Accident", "Damaged/Dropped", "Staff Sample", "Donated"],
                        key=f"reason_{item['item_id']}", label_visibility="collapsed")
                        
                with qty_col:
                    qty = st.number_input("Qty", min_value=1, max_value=remaining, value=remaining, 
                                         key=f"qty_{item['item_id']}", label_visibility="collapsed")
                                         
                with btn_col:
                    if st.button("Log Waste", key=f"log_{item['item_id']}", type="primary", use_container_width=True):
                        log_waste(item["item_id"], qty, reason)
                        st.session_state.waste_logged = f"✅ Logged {qty} {item['product_name']} as {reason}. AI updated!"
                        st.rerun()
            else:
                st.caption(f"Logged: {item['wasted']} units ({item['reason'] or 'N/A'})")

# AI Insights Section
st.markdown("---")
st.subheader("🤖 AI Learning from Today")
insights = get_ai_waste_insights()

if insights:
    cols = st.columns(3)
    for i, insight in enumerate(insights[:3]):
        with cols[i % 3]:
            st.metric(insight["waste_reason"] or "Unknown", f"{insight['total_wasted']} units", f"{insight['occurrences']} times")
    st.caption("💡 AI will adjust tomorrow's recommendations based on these patterns.")
else:
    st.caption("Log waste today to start building AI insights.")