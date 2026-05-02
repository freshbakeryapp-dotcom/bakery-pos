import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()

# ---- CUSTOM BAKERY STYLING ----
st.markdown("""
<style>
    /* Warm bakery palette */
    :root {
        --cream: #FFF8F0;
        --sage: #7A9A7E;
        --sage-dark: #5C7A60;
        --caramel: #C4956A;
        --caramel-light: #F5E6D3;
        --charcoal: #3D3430;
        --soft-white: #FFFAF5;
    }
    
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp {
        margin-top: -60px;
        background: var(--soft-white);
    }
    
    /* Typography */
    h1, h2, h3, .total-text {
        font-family: 'Georgia', serif;
        color: var(--charcoal);
    }
    
    /* Product buttons */
    .stButton > button {
        height: 65px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1.5px solid #E8DDD5;
        background: white;
        color: var(--charcoal);
        transition: all 0.1s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stButton > button:hover {
        border-color: var(--sage);
        background: #F8F6F3;
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }
    .stButton > button:active {
        background: var(--sage);
        color: white;
        border-color: var(--sage-dark);
    }
    
    /* Category pills */
    .cat-active button {
        background: var(--sage) !important;
        color: white !important;
        border-color: var(--sage-dark) !important;
    }
    
    /* Quantity buttons */
    .qty-row button {
        height: 32px !important;
        width: 32px !important;
        padding: 0 !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }
    
    /* PAY button */
    .pay-btn button {
        height: 60px !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        background: var(--sage) !important;
        color: white !important;
        border: none !important;
        letter-spacing: 1px;
    }
    .pay-btn button:hover {
        background: var(--sage-dark) !important;
    }
    
    /* Cart item */
    .cart-item {
        padding: 10px 0;
        border-bottom: 1px solid #F0EBE5;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin: 2px;
    }
    .badge-fresh { background: #E8F5E9; color: #2E7D32; }
    .badge-popular { background: #FFF3E0; color: #E65100; }
    .badge-new { background: #E3F2FD; color: #1565C0; }
    
    /* Divider */
    hr { border-color: #E8DDD5; }
</style>
""", unsafe_allow_html=True)

conn = get_db()

# Session state
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False
if 'active_category' not in st.session_state:
    st.session_state.active_category = None
if 'order_note' not in st.session_state:
    st.session_state.order_note = ""

def cart_total():
    return sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

def cart_count():
    return sum(item['qty'] for item in st.session_state.cart.values())

# ---- HEADER ----
header = st.columns([3, 1.5, 1])
header[0].markdown("# 🥖 Bakery POS")
store = header[1].selectbox(
    "📍 Store",
    ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    label_visibility="collapsed"
)
header[2].markdown(f"<div style='text-align:right; padding-top:15px; font-size:1.1rem;'><b>🛒 {cart_count()}</b> items</div>", unsafe_allow_html=True)

st.divider()

# ---- SALE COMPLETE SCREEN ----
if st.session_state.sale_done:
    st.success("## ✅ Order Complete!")
    st.balloons()
    
    if st.session_state.get('last_order'):
        st.markdown(f"<div class='total-text' style='font-size:2.5rem; text-align:center;'>${st.session_state.last_order['total']:.2f}</div>", unsafe_allow_html=True)
        for item in st.session_state.last_order['items']:
            st.write(f"• {item['name']} ×{item['qty']}")
    
    if st.button("🆕 New Order", type="primary", use_container_width=True):
        st.session_state.sale_done = False
        st.session_state.last_order = None
        st.session_state.active_category = None
        st.session_state.order_note = ""
        st.rerun()

else:
    # ---- MAIN POS ----
    left_panel, right_panel = st.columns([2, 1])
    
    with left_panel:
        # ---- CATEGORY FILTER CHIPS ----
        categories = conn.execute(
            "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category"
        ).fetchall()
        cat_list = [c['category'] for c in categories]
        
        if cat_list:
            cat_cols = st.columns(len(cat_list) + 1)
            
            is_all = st.session_state.active_category is None
            all_label = "📋 All"
            if cat_cols[0].button(all_label, key="cat_all", use_container_width=True,
                                   help="Show all products"):
                st.session_state.active_category = None
                st.rerun()
            
            for i, cat in enumerate(cat_list):
                is_active = st.session_state.active_category == cat
                emoji_map = {"Bread": "🍞", "Pastry": "🥐", "Local": "🍡", "Savoury": "🥧", "Cake": "🎂"}
                emoji = emoji_map.get(cat, "📦")
                label = f"{emoji} {cat}"
                
                if is_active:
                    st.markdown(f"<style>div[data-testid='stHorizontalBlock'] div:nth-child({i+2}) button {{background: #7A9A7E !important; color: white !important;}}</style>", unsafe_allow_html=True)
                
                if cat_cols[i + 1].button(label, key=f"cat_{cat}", use_container_width=True):
                    st.session_state.active_category = cat
                    st.rerun()
        
        st.divider()
        
        # ---- PRODUCT GRID ----
        if st.session_state.active_category:
            products = conn.execute(
                "SELECT id, name, price, category FROM products WHERE category = ? ORDER BY name",
                (st.session_state.active_category,)
            ).fetchall()
        else:
            products = conn.execute(
                "SELECT id, name, price, category FROM products ORDER BY category, name"
            ).fetchall()
        
        if products:
            cols = st.columns(3)
            for i, product in enumerate(products):
                with cols[i % 3]:
                    pid = str(product['id'])
                    in_cart = pid in st.session_state.cart
                    qty = st.session_state.cart[pid]['qty'] if in_cart else 0
                    
                    # Product name with optional badge
                    name = product['name']
                    qty_indicator = f" · ×{qty}" if qty > 0 else ""
                    
                    # Random badge for visual interest (in real app, stored in DB)
                    badge = ""
                    if i % 4 == 0:
                        badge = " <span class='badge badge-fresh'>Fresh</span>"
                    elif i % 4 == 1:
                        badge = " <span class='badge badge-popular'>Popular</span>"
                    
                    label = f"{name}{qty_indicator}\n${product['price']:.2f}"
                    
                    if st.button(label, key=f"add_{product['id']}", use_container_width=True):
                        if in_cart:
                            st.session_state.cart[pid]['qty'] += 1
                        else:
                            st.session_state.cart[pid] = {
                                'name': product['name'],
                                'price': product['price'],
                                'category': product['category'],
                                'qty': 1
                            }
                        st.rerun()
        else:
            st.info("No products in this category")
    
    with right_panel:
        # ---- ORDER TICKET ----
        st.markdown(f"<h3 style='font-family:Georgia,serif;'>🧾 Order Ticket</h3>", unsafe_allow_html=True)
        
        if st.session_state.cart:
            cart_items = list(st.session_state.cart.items())
            
            for pid, item in cart_items:
                item_total = item['price'] * item['qty']
                
                r_cols = st.columns([3, 1.8, 1])
                
                # Product name + price per unit
                r_cols[0].markdown(f"""
                <div class='cart-item'>
                    <b>{item['name'][:18]}</b><br>
                    <span style='color:#888; font-size:0.8rem;'>${item['price']:.2f} each</span>
                </div>
                """, unsafe_allow_html=True)
                
                # Quantity controls
                qty_cols = r_cols[1].columns([1, 1.2, 1])
                if qty_cols[0].button("−", key=f"m_{pid}"):
                    if st.session_state.cart[pid]['qty'] > 1:
                        st.session_state.cart[pid]['qty'] -= 1
                    else:
                        del st.session_state.cart[pid]
                    st.rerun()
                
                qty_cols[1].markdown(f"<div style='text-align:center; padding-top:5px; font-weight:700; font-size:1.1rem;'>{item['qty']}</div>", unsafe_allow_html=True)
                
                if qty_cols[2].button("+", key=f"p_{pid}"):
                    st.session_state.cart[pid]['qty'] += 1
                    st.rerun()
                
                # Item total
                r_cols[2].markdown(f"<div style='text-align:right; padding-top:8px; font-weight:600;'>${item_total:.2f}</div>", unsafe_allow_html=True)
            
            st.divider()
            
            # Order note
            st.session_state.order_note = st.text_input(
                "Order note (optional)",
                value=st.session_state.order_note,
                placeholder="e.g., Extra crispy, no sesame...",
                key="order_note_input"
            )
            
            st.divider()
            
            # Total
            total = cart_total()
            st.markdown(f"""
            <div style='text-align:center; margin:10px 0;'>
                <div style='font-size:0.9rem; color:#888;'>{cart_count()} items</div>
                <div class='total-text' style='font-size:2.2rem; font-weight:700;'>${total:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            col1, col2 = st.columns(2)
            if col1.button("🗑️ Void", use_container_width=True, help="Clear entire order"):
                st.session_state.cart = {}
                st.session_state.order_note = ""
                st.rerun()
            
            st.markdown("<div class='pay-btn'>", unsafe_allow_html=True)
            if st.button("💳 Checkout", key="pay", use_container_width=True):
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
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("👈 Select a category, then tap products to build your order")

conn.close()