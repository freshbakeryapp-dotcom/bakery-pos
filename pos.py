import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()

st.title("🧾 Point of Sale")

conn = get_db()

# Store selector at top
store = st.selectbox(
    "📍 Store",
    ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    key="pos_store"
)

# Initialize cart
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False

if st.session_state.sale_done:
    st.success(f"✅ Sale completed at {store}!")
    st.balloons()
    
    # Show order summary
    if st.session_state.get('last_order'):
        st.write("**Order summary:**")
        total = 0
        for item in st.session_state.last_order:
            st.write(f"- {item['name']}: ${item['price']:.2f}")
            total += item['price']
        st.markdown(f"### Total: ${total:.2f}")
    
    if st.button("🆕 New Sale", type="primary", use_container_width=True):
        st.session_state.sale_done = False
        st.session_state.last_order = None
        st.rerun()

else:
    # Split into products (left) and cart (right)
    left, right = st.columns([3, 2])
    
    with left:
        st.subheader("📦 Products")
        
        products = conn.execute("SELECT id, name, price, category FROM products ORDER BY category, name").fetchall()
        
        # Group by category
        categories = {}
        for p in products:
            cat = p['category'] or 'Other'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
        
        for cat, prods in categories.items():
            st.markdown(f"**{cat}**")
            cols = st.columns(3)
            for i, product in enumerate(prods):
                with cols[i % 3]:
                    # Product card
                    st.markdown(f"""
                    <div style="border:1px solid #e0e0e0; border-radius:12px; padding:15px; margin:5px 0; text-align:center;">
                        <div style="font-size:1.1rem; font-weight:600;">{product['name']}</div>
                        <div style="font-size:1.3rem; color:#4CAF50; font-weight:700;">${product['price']:.2f}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"➕ Add", key=f"add_{product['id']}", use_container_width=True):
                        st.session_state.cart.append({
                            'id': product['id'],
                            'name': product['name'],
                            'price': product['price'],
                            'quantity': 1
                        })
                        st.rerun()
    
    with right:
        st.subheader("🛒 Current Order")
        
        if st.session_state.cart:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                cols = st.columns([4, 1, 1])
                cols[0].write(f"**{item['name']}**")
                cols[1].write(f"${item['price']:.2f}")
                if cols[2].button("✕", key=f"rm_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
                total += item['price']
            
            st.markdown("---")
            st.markdown(f"<div style='text-align:center;'><span style='font-size:1.5rem; font-weight:700;'>Total: ${total:.2f}</span></div>", unsafe_allow_html=True)
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            if col1.button("🗑️ Clear", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            
            if col2.button("💳 Pay", type="primary", use_container_width=True):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state.cart:
                    conn.execute(
                        "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (item['id'], store, 1, item['price'], item['price'], timestamp)
                    )
                conn.commit()
                st.session_state.last_order = st.session_state.cart.copy()
                st.session_state.cart = []
                st.session_state.sale_done = True
                st.rerun()
        else:
            st.info("👆 Tap products on the left to add them to the order.")

conn.close()