import streamlit as st

st.set_page_config(page_title="BakeryOS", layout="wide")

page = st.sidebar.radio("Navigate", ["🧾 POS", "📊 Dashboard", "📦 Products"])

if page == "🧾 POS":
    exec(open("pos.py", encoding="utf-8").read())
elif page == "📊 Dashboard":
    exec(open("dashboard.py", encoding="utf-8").read())
elif page == "📦 Products":
    exec(open("products.py", encoding="utf-8").read())