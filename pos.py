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
    .stApp {margin-top: -60px; background: #FAFAFA;}
    
    /* Product buttons */
    .stButton > button {
        height: 60px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.85rem;
        border: 1px solid #E0E0E0;
        background: white;
        color: #1A1A1A;
    }
    .stButton > button:hover {
        border-color: #1A1A1A;
        background: #F5F5F5;
    }
    
    /* Category buttons */
    .cat-btn button {
        border-radius: 20px;
        font-size: 0.8rem;
        padding: 4px 16px;
        height: 36px;
    }
    
    /* Quantity buttons */
    .qty-col button {
        height: 32px;
        width: 32px;
        padding: 0;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 6px;
    }
    
    /* Checkout button */
    .checkout-btn button {
        height: 56px;
        font-size: 1.1rem;
        font-weight: 600;
        background: #1A1A1A;
        color: white;
        border: none;
        border-radius: 8px;
    }
    .checkout-btn button:hover {
        background: #333;
    }
    
    hr {border-color: #EEEEEE; margin: 12px 0;}
</style>
""", unsafe_allow_html=True)

conn = get_db()

if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False
if 'active_category' not in st.session_state:
    st.session_state.active_category = None

def cart_total():
    return sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

def cart_count():
    return sum(item['qty'] for item in st.session_state.cart.values())

# ---- HEADER ----
h = st.columns([3, 2, 1])
h[0].markdown("## 🧾 POS")
store = h[1].selectbox("Store", ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"], label_visibility="collapsed")
h[2].markdown(f"<div style='padding-top:12px; font-size:1rem; color:#666;'>{cart_count()} items</div>", unsafe_allow_html=True)
st.divider()

if st.session_state.sale_done:
    st.success("Order complete")
    if st.session_state.get('last_order'):
        st.markdown(f"## ${st.session_state.last_order['total']:.2f}")
        for item in st.session_state.last_order['items']:
            st.write(f"{item['name']} ×{item['qty']}")
    if st.button("New Order", type="primary", use_container_width=True):
        st.session_state.sale_done = False
        st.session_state.last_order = None
        st.session_state.active_category = None
        st.rerun()

else:
    left, right = st.columns([2, 1])
    
    with left:
        # Categories
        cats = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category").fetchall()
        cat_list = [c['category'] for c in cats]
        
        if cat_list:
            cols = st.columns(len(cat_list) + 1)
            if cols[0].button("All", key="c_all", use_container_width=True):
                st.session_state.active_category = None
                st.rerun()
            for i, cat in enumerate(cat_list):
                if cols[i+1].button(cat, key=f"c_{cat}", use_container_width=True):
                    st.session_state.active_category = cat
                    st.rerun()
        
        st.divider()
        
        # Products
        if st.session_state.active_category:
            products = conn.execute("SELECT id, name, price FROM products WHERE category=? ORDER BY name", (st.session_state.active_category,)).fetchall()
        else:
            products = conn.execute("SELECT id, name, price FROM products ORDER BY category, name").fetchall()
        
        if products:
            cols = st.columns(3)
            for i, p in enumerate(products):
                with cols[i % 3]:
                    pid = str(p['id'])
                    qty = st.session_state.cart[pid]['qty'] if pid in st.session_state.cart else 0
                    label = f"{p['name']}{' ×'+str(qty) if qty else ''}\n${p['price']:.2f}"
                    if st.button(label, key=f"p_{p['id']}", use_container_width=True):
                        if pid in st.session_state.cart:
                            st.session_state.cart[pid]['qty'] += 1
                        else:
                            st.session_state.cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': 1}
                        st.rerun()
    
    with right:
        st.markdown("### Order")
        
        if st.session_state.cart:
            for pid, item in st.session_state.cart.items():
                c = st.columns([2.5, 1.5, 1])
                c[0].markdown(f"**{item['name'][:16]}**<br><span style='color:#888; font-size:0.8rem;'>${item['price']:.2f}</span>", unsafe_allow_html=True)
                
                qc = c[1].columns([1, 1, 1])
                if qc[0].button("−", key=f"m_{pid}"):
                    if st.session_state.cart[pid]['qty'] > 1:
                        st.session_state.cart[pid]['qty'] -= 1
                    else:
                        del st.session_state.cart[pid]
                    st.rerun()
                qc[1].markdown(f"<div style='text-align:center; padding-top:3px; font-weight:600;'>{item['qty']}</div>", unsafe_allow_html=True)
                if qc[2].button("+", key=f"pl_{pid}"):
                    st.session_state.cart[pid]['qty'] += 1
                    st.rerun()
                
                c[2].markdown(f"<div style='text-align:right; padding-top:8px; font-weight:500;'>${item['price']*item['qty']:.2f}</div>", unsafe_allow_html=True)
            
            st.divider()
            total = cart_total()
            st.markdown(f"<div style='text-align:center; font-size:2rem; font-weight:700;'>${total:.2f}</div>", unsafe_allow_html=True)
            st.caption(f"{cart_count()} items")
            
            c1, c2 = st.columns(2)
            if c1.button("Clear", use_container_width=True):
                st.session_state.cart = {}
                st.rerun()
            
            st.markdown("<div class='checkout-btn'>", unsafe_allow_html=True)
            if st.button("Checkout", key="pay", use_container_width=True):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                order_items = []
                for pid, item in st.session_state.cart.items():
                    for _ in range(item['qty']):
                        conn.execute("INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?,?,?,?,?,?)", (int(pid), store, 1, item['price'], item['price'], ts))
                    order_items.append({'name': item['name'], 'price': item['price'], 'qty': item['qty']})
                conn.commit()
                st.session_state.last_order = {'items': order_items, 'total': total}
                st.session_state.cart = {}
                st.session_state.sale_done = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Select a category and tap products")

conn.close()