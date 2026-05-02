import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Artisan Crumb - Bakery OS",
    page_icon="🥐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load custom CSS
try:
    with open('styles.css', encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'POS'
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'store' not in st.session_state:
    st.session_state.store = 'Gadong'

# Header
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<h1 style="font-family: \'Playfair Display\', serif; color: #3C2415; margin: 0;">🥐 Artisan Crumb</h1>', unsafe_allow_html=True)
with col2:
    store_options = ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"]
    selected_store = st.selectbox("Store", store_options, index=store_options.index(st.session_state.store), label_visibility="collapsed")
    st.session_state.store = selected_store

st.markdown('<div style="height: 1px; background: linear-gradient(90deg, #E8DCC8, transparent); margin: 1.5rem 0;"></div>', unsafe_allow_html=True)

# Navigation
# We have 8 pages now: POS, Dashboard, Products, Events, Ordering, Prep List, Wrap-Up, ROI
nav_cols = st.columns(8)
pages = [
    ("🧾 POS", "POS"), 
    ("📊 Dashboard", "Dashboard"), 
    ("📦 Products", "Products"), 
    ("📅 Events", "Events"), 
    ("📦 Ordering", "Ordering"), 
    ("📋 Prep List", "Prep List"), 
    ("🌙 Wrap-Up", "Wrap-Up"), 
    ("💰 ROI", "ROI")
]

for i, (label, page_name) in enumerate(pages):
    with nav_cols[i]:
        is_active = st.session_state.page == page_name
        if st.button(label, key=f"nav_{page_name}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.page = page_name
            st.rerun()

st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

# Page routing
if st.session_state.page == 'POS':
    exec(open("pos.py", encoding="utf-8").read())
elif st.session_state.page == 'Dashboard':
    exec(open("dashboard.py", encoding="utf-8").read())
elif st.session_state.page == 'Products':
    exec(open("products.py", encoding="utf-8").read())
elif st.session_state.page == 'Events':
    exec(open("events_page.py", encoding="utf-8").read())
elif st.session_state.page == 'Ordering':
    exec(open("ordering_page.py", encoding="utf-8").read())
elif st.session_state.page == 'Prep List':
    exec(open("prep_list_page.py", encoding="utf-8").read())
elif st.session_state.page == 'Wrap-Up':
    exec(open("wrap_up_page.py", encoding="utf-8").read())
elif st.session_state.page == 'ROI':
    exec(open("roi_page.py", encoding="utf-8").read())
else:
    st.error("Page not found.")