import streamlit as st

st.set_page_config(page_title="BakeryOS", layout="wide")

# Simple sidebar navigation
page = st.sidebar.radio("Navigate", ["🧾 POS", "📊 Dashboard"])

if page == "🧾 POS":
    exec(open("pos.py", encoding="utf-8").read())
else:
    exec(open("dashboard.py", encoding="utf-8").read())