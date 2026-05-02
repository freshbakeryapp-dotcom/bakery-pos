import streamlit as st

st.set_page_config(
    page_title="BakeryOS",
    page_icon="🥖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
    }
    .product-card {
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin: 5px;
        cursor: pointer;
    }
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .big-number {
        font-size: 2.5rem;
        font-weight: 700;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 15px;
    }
    .plan-item {
        border-left: 4px solid #4CAF50;
        padding: 10px 15px;
        margin: 8px 0;
        background: #f9f9f9;
        border-radius: 8px;
    }
    .plan-item.warning {
        border-left-color: #FF9800;
    }
    .plan-item.danger {
        border-left-color: #f44336;
    }
</style>
""", unsafe_allow_html=True)

# Top navigation as radio buttons styled as tabs
page = st.radio(
    "",
    ["🧾 POS", "📊 Dashboard", "📦 Products", "📅 Events"],
    horizontal=True,
    label_visibility="collapsed"
)

if page == "🧾 POS":
    exec(open("pos.py", encoding="utf-8").read())
elif page == "📊 Dashboard":
    exec(open("dashboard.py", encoding="utf-8").read())
elif page == "📦 Products":
    exec(open("products.py", encoding="utf-8").read())
elif page == "📅 Events":
    exec(open("events_page.py", encoding="utf-8").read())