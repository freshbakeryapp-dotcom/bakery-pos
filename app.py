import streamlit as st

st.set_page_config(
    page_title="BakeryOS",
    page_icon="🥖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inject CSS directly — no file loading
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; }
    .stApp { margin-top: -60px; background: #FAFAFA; }
    
    .stButton > button {
        height: 48px !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        border: 1px solid #E0E0E0 !important;
        background: white !important;
        color: #1A1A1A !important;
    }
    .stButton > button:hover {
        border-color: #1A1A1A !important;
        background: #F5F5F5 !important;
    }
    .stButton > button[kind="primary"] {
        background: #1A1A1A !important;
        color: white !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #333 !important;
    }
    
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E0E0E0;
        border-radius: 12px;
        padding: 16px;
    }
    
    hr { border-color: #EEEEEE !important; }
    
    .stTabs [data-baseweb="tab"] {
        font-weight: 500;
        font-size: 0.9rem;
    }
    
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #DDD; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# Navigation
page = st.radio(
    "Navigation",
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