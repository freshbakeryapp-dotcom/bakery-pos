import streamlit as st

st.set_page_config(
    page_title="BakeryOS",
    page_icon="🥖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load global CSS
def load_css():
    with open("styles/global.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

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