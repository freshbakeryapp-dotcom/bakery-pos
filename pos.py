import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db
import os

init_db()

st.set_page_config(page_title="Bakery POS", layout="wide")
st.title("🧾 Bakery POS")

store = st.selectbox("Store", ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"])

# Use a single connection for the whole page load
conn = get_db()
products = conn.execute("SELECT id, name, price FROM products").fetchall()

if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sale_completed' not in st.session_state:
    st.session_state.sale_completed = False

# Debug sidebar
st.sidebar.write(f"DB Path: {os.path.abspath('bakery.db')}")
st.sidebar.write(f"DB Exists: {os.path.exists('bakery.db')}")
sales_count = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()
st.sidebar.write(f"Sales in DB: {sales_count['cnt']}")

if st.session_state.sale_completed:
    st.success(f"✅ Sale completed at {st.session_state.last_store}!")
    st.balloons()
    if st.button("🆕 New Sale"):
        st.session_state.sale_completed = False
        st.session_state.last_store = None
        st.rerun()
else:
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

    st.markdown("---")
    st.subheader("🛒 Current Order")
    
    if st.session_state.cart:
        total = 0
        for i, item in enumerate(st.session_state.cart):
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(item['name'])
            col2.write(f"${item['price']:.2f}")
            if col3.button("❌", key=f"remove_{i}"):
                st.session_state.cart.pop(i)
                st.rerun()
            total += item['price']
        
        st.markdown(f"### Total: ${total:.2f}")
        
        if st.button("💳 Complete Sale", type="primary"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for item in st.session_state.cart:
                conn.execute(
                    "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (item['id'], store, item['quantity'], item['price'], item['price'], timestamp)
                )
            conn.commit()
            
            st.session_state.cart = []
            st.session_state.sale_completed = True
            st.session_state.last_store = store
            st.rerun()
        
        if st.button("🗑️ Clear Cart"):
            st.session_state.cart = []
            st.rerun()
    else:
        st.info("Cart is empty. Add products above.")

conn.close()