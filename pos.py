import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()

st.set_page_config(page_title="POS", layout="wide")

st.markdown("""
<style>
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {margin-top: -60px;}
    .stButton button {height: 55px; border-radius: 10px; font-weight: 600; font-size: 0.85rem;}
    .qty-btn button {height: 35px; width: 35px; padding: 0; font-size: 1.2rem; font-weight: 700; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

conn = get_db()

# Session state
if 'cart' not in st.session_state:
    st.session_state.cart = {}  # Changed to dict: {product_id: {name, price, qty}}
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False
if 'active_category' not in st.session_state:
    st.session_state.active_category = None

# Helper: count items
def cart_total_items():
    return sum(item['qty'] for item in st.session_state.cart.values())

def cart_total_price():
    return sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

# ---- TOP BAR ----
top_cols = st.columns([2, 2, 1])
top_cols[0].markdown("## 🧾 POS")
store = top_cols[1].selectbox(
    "📍",
    ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    label_visibility="collapsed"
)
top_cols[2].markdown(f"**🛒 {cart_total_items()} items**")

st.divider()

if st.session_state.sale_done:
    # ---- SALE COMPLETE ----
    st.success(f"✅ Sale completed at {store}!")
    st.balloons()
    
    if st.session_state.get('last_order'):
        total = st.session_state.last_order['total']
        st.markdown(f"## Total: ${total:.2f}")
        for item in st.session_state.last_order['items']:
            st.write(f"- {item['name']} x{item['qty']} = ${item['price'] * item['qty']:.2f}")
    
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
        
        cat_cols = st.columns(len(categories) + 1)
        
        if cat_cols[0].button("📋 All", key="cat_all", use_container_width=True):
            st.session_state.active_category = None
            st.rerun()
        
        for i, cat in enumerate(categories):
            label = f"🍞 {cat}" if cat != "All" else cat
            if cat_cols[i + 1].button(label, key=f"cat_{cat}", use_container_width=True):
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
            filtered = conn.execute("SELECT id, name, price FROM products ORDER BY category, name").fetchall()
            st.caption("Showing: All")
        
        if filtered:
            cols = st.columns(3)
            for i, product in enumerate(filtered):
                with cols[i % 3]:
                    pid = str(product['id'])
                    in_cart = pid in st.session_state.cart
                    qty = st.session_state.cart[pid]['qty'] if in_cart else 0
                    
                    # Product card with quantity indicator
                    qty_badge = f" [x{qty}]" if qty > 0 else ""
                    label = f"{product['name']}{qty_badge}\n${product['price']:.2f}"
                    
                    if st.button(label, key=f"add_{product['id']}", use_container_width=True):
                        if in_cart:
                            st.session_state.cart[pid]['qty'] += 1
                        else:
                            st.session_state.cart[pid] = {
                                'name': product['name'],
                                'price': product['price'],
                                'qty': 1
                            }
                        st.rerun()
        else:
            st.info("No products in this category")
    
    with right:
        # ---- CART ----
        st.markdown("### 🛒 Order")
        
        if st.session_state.cart:
            cart_items = list(st.session_state.cart.items())
            
            for pid, item in cart_items:
                # Row: name | qty controls | price | remove
                r_cols = st.columns([2.5, 1.5, 1, 0.8])
                r_cols[0].write(f"**{item['name'][:15]}**")
                
                # Quantity controls
                qty_cols = r_cols[1].columns([1, 1, 1])
                if qty_cols[0].button("−", key=f"minus_{pid}", help="Decrease"):
                    if st.session_state.cart[pid]['qty'] > 1:
                        st.session_state.cart[pid]['qty'] -= 1
                    else:
                        del st.session_state.cart[pid]
                    st.rerun()
                
                qty_cols[1].markdown(f"<div style='text-align:center; font-weight:600;'>{item['qty']}</div>", unsafe_allow_html=True)
                
                if qty_cols[2].button("+", key=f"plus_{pid}", help="Increase"):
                    st.session_state.cart[pid]['qty'] += 1
                    st.rerun()
                
                r_cols[2].write(f"${item['price'] * item['qty']:.2f}")
                
                if r_cols[3].button("✕", key=f"rm_{pid}", help="Remove"):
                    del st.session_state.cart[pid]
                    st.rerun()
            
            st.divider()
            
            # Total
            total = cart_total_price()
            total_items = cart_total_items()
            st.markdown(f"**{total_items} items**")
            st.markdown(f"## ${total:.2f}")
            
            col1, col2 = st.columns(2)
            if col1.button("🗑️ Clear", use_container_width=True):
                st.session_state.cart = {}
                st.rerun()
            
            if col2.button("💳 PAY", type="primary", use_container_width=True):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                order_items = []
                for pid, item in st.session_state.cart.items():
                    for _ in range(item['qty']):
                        conn.execute(
                            "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                            (int(pid), store, 1, item['price'], item['price'], timestamp)
                        )
                    order_items.append({'name': item['name'], 'price': item['price'], 'qty': item['qty']})
                conn.commit()
                st.session_state.last_order = {'items': order_items, 'total': total}
                st.session_state.cart = {}
                st.session_state.sale_done = True
                st.rerun()
        else:
            st.info("👈 Tap a product to add it")

conn.close()