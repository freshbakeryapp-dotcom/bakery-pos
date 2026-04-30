import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

# Initialize DB on first run
init_db()

st.set_page_config(page_title="Bakery POS", layout="wide")
st.title("🧾 Bakery POS")

# Store selector
store = st.selectbox("Store", ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"])

# Load products
conn = get_db()
products = conn.execute("SELECT id, name, price FROM products").fetchall()
conn.close()

# Cart in session state
if 'cart' not in st.session_state:
    st.session_state.cart = []

# Product grid
st.subheader("Products")
cols = st.columns(3)
for i, product in enumerate(products):
    with cols[i % 3]:
        st.markdown(f"**{product['name']}**")
        st.caption(f"${product['price']:.2f}")
        if st.button(f"Add", key=f"add_{product['id']}"):
            st.session_state.cart.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': 1
            })
            st.rerun()

# Cart
st.subheader("🛒 Current Order")
if st.session_state.cart:
    total = 0
    for item in st.session_state.cart:
        st.write(f"{item['name']} — ${item['price']:.2f}")
        total += item['price']
    
    st.markdown(f"### Total: ${total:.2f}")
    
    if st.button("💳 Complete Sale", type="primary"):
        conn = get_db()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for item in st.session_state.cart:
            conn.execute(
                "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (item['id'], store, item['quantity'], item['price'], item['price'], timestamp)
            )
        conn.commit()
        conn.close()
        st.session_state.cart = []
        st.success(f"✅ Sale completed at {store}!")
        st.balloons()
        st.rerun()
    
    if st.button("🗑️ Clear Cart"):
        st.session_state.cart = []
        st.rerun()
else:
    st.info("Cart is empty. Add products above.")