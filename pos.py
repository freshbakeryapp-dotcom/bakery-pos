import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()

st.set_page_config(page_title="POS", layout="wide")

# Hide Streamlit decorations
st.markdown("""
<style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {margin-top: -60px;}
    .stButton button {height: 60px; border-radius: 10px; font-weight: 600; font-size: 0.9rem;}
    .category-btn button {background: #f0f0f0; border: 2px solid #e0e0e0;}
    .category-btn.active button {background: #4CAF50; color: white; border-color: #388E3C;}
    .pay-btn button {height: 60px; font-size: 1.2rem; background: #4CAF50; color: white;}
</style>
""", unsafe_allow_html=True)

conn = get_db()

# Session state
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False
if 'active_category' not in st.session_state:
    st.session_state.active_category = None

# ---- TOP BAR ----
top_cols = st.columns([2, 2, 1])
top_cols[0].markdown("## 🧾 POS")
store = top_cols[1].selectbox(
    "📍",
    ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    label_visibility="collapsed"
)
top_cols[2].markdown(f"**🛒 {len(st.session_state.cart)}**")

st.divider()

if st.session_state.sale_done:
    # ---- SALE COMPLETE ----
    st.success(f"✅ Sale completed at {store}!")
    st.balloons()
    
    if st.session_state.get('last_order'):
        total = sum(item['price'] for item in st.session_state.last_order)
        st.markdown(f"## Total: ${total:.2f}")
        for item in st.session_state.last_order:
            st.write(f"- {item['name']}")
    
    if st.button("🆕 NEW SALE", type="primary", use_container_width=True):
        st.session_state.sale_done = False
        st.session_state.last_order = None
        st.session_state.active_category = None
        st.rerun()

else:
    # ---- MAIN LAYOUT ----
    left, right = st.columns([1.8, 1])
    
    with left:
        # ---- CATEGORY TABS ----
        products = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category").fetchall()
        categories = [p['category'] for p in products]
        
        if not categories:
            categories = ["All"]
        
        # Category buttons row
        cat_cols = st.columns(len(categories) + 1)
        
        # "All" button
        if cat_cols[0].button("📋 All", key="cat_all", use_container_width=True,
                              help="Show all products"):
            st.session_state.active_category = None
            st.rerun()
        
        for i, cat in enumerate(categories):
            if cat_cols[i + 1].button(f"🍞 {cat}", key=f"cat_{cat}", use_container_width=True,
                                       help=f"Show {cat}"):
                st.session_state.active_category = cat
                st.rerun()
        
        st.divider()
        
        # ---- PRODUCT GRID ----
        if st.session_state.active_category:
            filtered = conn.execute(
                "SELECT id, name, price FROM products WHERE category = ? ORDER BY name",
                (st.session_state.active_category,)
            ).fetchall()
            st.caption(f"Showing: {st.session_state.active_category}")
        else:
            filtered = conn.execute("SELECT id, name, price, category FROM products ORDER BY category, name").fetchall()
            st.caption("Showing: All products")
        
        if filtered:
            cols = st.columns(3)
            for i, product in enumerate(filtered):
                with cols[i % 3]:
                    # Product button
                    label = f"{product['name']}\n${product['price']:.2f}"
                    if st.button(label, key=f"add_{product['id']}", use_container_width=True):
                        st.session_state.cart.append({
                            'id': product['id'],
                            'name': product['name'],
                            'price': product['price'],
                        })
                        st.rerun()
        else:
            st.info("No products in this category")
    
    with right:
        # ---- CART ----
        st.markdown("### 🛒 Order")
        
        if st.session_state.cart:
            total = 0
            for i, item in enumerate(st.session_state.cart):
                r_cols = st.columns([3, 1, 1])
                r_cols[0].write(item['name'][:20])
                r_cols[1].write(f"${item['price']:.2f}")
                if r_cols[2].button("✕", key=f"rm_{i}", help="Remove"):
                    st.session_state.cart.pop(i)
                    st.rerun()
                total += item['price']
            
            st.divider()
            st.markdown(f"## ${total:.2f}")
            
            col1, col2 = st.columns(2)
            if col1.button("🗑️ Clear", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            
            if col2.button("💳 PAY", type="primary", use_container_width=True):
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
            st.info("👈 Tap a category, then tap products to add")

conn.close()