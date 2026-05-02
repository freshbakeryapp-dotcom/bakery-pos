import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()

# Hide Streamlit header/footer for cleaner POS look
st.markdown("""
<style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {margin-top: -60px;}
    .pos-container {height: calc(100vh - 80px);}
    .product-grid {height: calc(100vh - 200px); overflow-y: auto; padding-right: 10px;}
    .cart-container {height: calc(100vh - 280px); overflow-y: auto;}
    .product-btn {width: 100%; height: 70px; margin: 3px 0; border-radius: 10px; font-size: 0.85rem; font-weight: 600;}
    .cart-item {padding: 8px 0; border-bottom: 1px solid #f0f0f0;}
    .total-bar {position: fixed; bottom: 0; right: 0; background: white; padding: 15px; border-top: 2px solid #4CAF50; width: 100%;}
</style>
""", unsafe_allow_html=True)

conn = get_db()

# Initialize cart
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False

# ---- TOP BAR ----
top_cols = st.columns([2, 1, 1])
top_cols[0].markdown("## 🧾 Bakery POS")
store = top_cols[1].selectbox("Store", 
    ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    label_visibility="collapsed"
)
cart_count = len(st.session_state.cart)
top_cols[2].markdown(f"**🛒 {cart_count} items**")

st.markdown("---")

if st.session_state.sale_done:
    # Sale complete screen
    st.success(f"✅ Sale completed at {store}!")
    st.balloons()
    
    if st.session_state.get('last_order'):
        total = sum(item['price'] for item in st.session_state.last_order)
        st.markdown(f"### Total: ${total:.2f}")
        for item in st.session_state.last_order:
            st.write(f"- {item['name']}")
    
    if st.button("🆕 New Sale", type="primary", use_container_width=True):
        st.session_state.sale_done = False
        st.session_state.last_order = None
        st.rerun()

else:
    # ---- MAIN POS LAYOUT ----
    left, right = st.columns([1.5, 1])
    
    # ---- LEFT: PRODUCTS ----
    with left:
        st.markdown("### 📦 Products")
        
        products = conn.execute("SELECT id, name, price, category FROM products ORDER BY category, name").fetchall()
        
        # Group by category
        categories = {}
        for p in products:
            cat = p['category'] or 'Other'
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)
        
        # Scrollable product area
        product_html = '<div class="product-grid">'
        
        for cat, prods in categories.items():
            product_html += f'<div style="color:#888; font-size:0.8rem; margin-top:10px;">{cat.upper()}</div>'
            product_html += '<div style="display:flex; flex-wrap:wrap; gap:5px;">'
            for product in prods:
                product_html += f'''
                <div style="flex:1; min-width:100px;">
                    <div style="border:1px solid #e0e0e0; border-radius:8px; padding:10px; text-align:center;">
                        <div style="font-weight:600; font-size:0.8rem;">{product['name'][:20]}</div>
                        <div style="color:#4CAF50; font-weight:700; font-size:1rem;">${product['price']:.2f}</div>
                    </div>
                </div>'''
            product_html += '</div>'
        
        product_html += '</div>'
        st.markdown(product_html, unsafe_allow_html=True)
        
        # Product buttons below cards
        cols = st.columns(3)
        flat_products = [p for prods in categories.values() for p in prods]
        for i, product in enumerate(flat_products):
            with cols[i % 3]:
                if st.button(f"{product['name']}\n${product['price']:.2f}", 
                           key=f"add_{product['id']}", 
                           use_container_width=True,
                           help=f"Add {product['name']}"):
                    st.session_state.cart.append({
                        'id': product['id'],
                        'name': product['name'],
                        'price': product['price'],
                    })
                    st.rerun()
    
    # ---- RIGHT: CART ----
    with right:
        st.markdown("### 🛒 Order")
        
        if st.session_state.cart:
            total = 0
            cart_items_html = '<div class="cart-container">'
            
            for i, item in enumerate(st.session_state.cart):
                cart_items_html += f'''
                <div class="cart-item">
                    <span style="font-weight:500;">{item['name'][:18]}</span>
                    <span style="float:right; font-weight:600;">${item['price']:.2f}</span>
                </div>'''
                total += item['price']
            
            cart_items_html += '</div>'
            st.markdown(cart_items_html, unsafe_allow_html=True)
            
            # Remove buttons
            for i, item in enumerate(st.session_state.cart):
                if st.button(f"✕ {item['name'][:15]}", key=f"rm_{i}", help="Remove item"):
                    st.session_state.cart.pop(i)
                    st.rerun()
            
            st.markdown("---")
            
            # Total and action buttons
            st.markdown(f"<div style='text-align:center; font-size:1.5rem; font-weight:700;'>${total:.2f}</div>", unsafe_allow_html=True)
            
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
            st.info("Tap a product to add it")

conn.close()