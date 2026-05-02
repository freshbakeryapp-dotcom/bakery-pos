import streamlit as st
import sqlite3
from datetime import datetime
from db import get_db, init_db

init_db()
conn = get_db()

# Initialize session state
if 'cart' not in st.session_state:
    st.session_state.cart = {}
if 'sale_done' not in st.session_state:
    st.session_state.sale_done = False
if 'active_category' not in st.session_state:
    st.session_state.active_category = None
if 'last_order' not in st.session_state:
    st.session_state.last_order = None

def cart_total():
    return sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

def cart_count():
    return sum(item['qty'] for item in st.session_state.cart.values())

# ========== SUCCESS SCREEN ==========
if st.session_state.sale_done and st.session_state.last_order:
    st.balloons()
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem; background: white; border-radius: 24px; box-shadow: 0 8px 24px rgba(60,36,21,0.1);">
        <div style="font-size: 4rem; margin-bottom: 1rem;">🎉</div>
        <h2 style="font-family: 'Playfair Display', serif; color: #3C2415; margin-bottom: 1rem;">Order Complete!</h2>
        <div style="font-size: 2.5rem; font-weight: 700; color: #8A9A7B;">${st.session_state.last_order['total']:.2f}</div>
        <p style="color: #6B5444; margin-top: 0.5rem;">{len(st.session_state.last_order['items'])} items</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button(" New Order", type="primary", use_container_width=True):
        st.session_state.update({'sale_done': False, 'last_order': None, 'cart': {}, 'active_category': None})
        st.rerun()
    conn.close()
    st.stop()

# ========== MAIN LAYOUT ==========
# Use gap="large" to prevent elements from squishing
left_col, right_col = st.columns([2.5, 1.2], gap="large")

# ========== LEFT: PRODUCT GRID ==========
with left_col:
    # Category tabs
    st.markdown('<div class="category-tabs">', unsafe_allow_html=True)
    cat_cols = st.columns(5)
    cats = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category").fetchall()
    cat_list = [c['category'] for c in cats]

    with cat_cols[0]:
        if st.button(" All", key="cat_all", use_container_width=True, type="primary" if st.session_state.active_category is None else "secondary"):
            st.session_state.active_category = None
            st.rerun()

    for i, cat in enumerate(cat_list[:4]):
        emoji = {"bread": "🥖", "pastry": "🥐", "local": "", "savoury": "🥧"}.get(cat.lower(), "📦")
        with cat_cols[i+1]:
            if st.button(f"{emoji} {cat}", key=f"cat_{cat}", use_container_width=True, type="primary" if st.session_state.active_category == cat else "secondary"):
                st.session_state.active_category = cat
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Product grid
    query = "SELECT id, name, price FROM products WHERE category = ? ORDER BY name" if st.session_state.active_category else "SELECT id, name, price FROM products ORDER BY name"
    params = (st.session_state.active_category,) if st.session_state.active_category else ()
    products = conn.execute(query, params).fetchall()

    if products:
        grid = st.columns(3)
        for i, p in enumerate(products):
            with grid[i % 3]:
                pid = str(p['id'])
                in_cart = pid in st.session_state.cart
                qty = st.session_state.cart[pid]['qty'] if in_cart else 0

                # Product Card Button
                # We use a fixed label structure to prevent resizing
                btn_text = f"{p['name']}\n${p['price']:.2f}"
                if in_cart:
                    btn_text = f"{p['name']}\n${p['price']:.2f}\n✓ {qty} in cart"
                
                # Key change: type="secondary" makes it a card, we style it via CSS
                if st.button(btn_text, key=f"prod_{pid}", use_container_width=True, type="secondary"):
                    if pid in st.session_state.cart:
                        st.session_state.cart[pid]['qty'] += 1
                    else:
                        st.session_state.cart[pid] = {'name': p['name'], 'price': p['price'], 'qty': 1}
                    st.rerun()
    else:
        st.info("📦 No products found. Add products in the Products page.")

# ========== RIGHT: CART PANEL ==========
with right_col:
    st.markdown('<div class="cart-panel">', unsafe_allow_html=True)
    st.markdown('<h3 style="font-family: \'Playfair Display\', serif; color: #3C2415; margin-bottom: 1.5rem;">🛒 Current Order</h3>', unsafe_allow_html=True)

    if st.session_state.cart:
        # Loop through cart
        for pid, item in list(st.session_state.cart.items()):
            # Use a container for the item row to keep layout tight
            with st.container():
                # Top row: Name and Price
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f'<div class="cart-item-name">{item["name"]}</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="cart-item-meta">${item["price"]:.2f} each</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="cart-item-total">${item["price"]*item["qty"]:.2f}</div>', unsafe_allow_html=True)
                
                # Bottom row: Quantity Controls (Inline)
                # We use 3 small columns for the buttons
                q1, q2, q3 = st.columns([1, 1, 1])
                with q1:
                    if st.button("−", key=f"dec_{pid}", use_container_width=True):
                        if st.session_state.cart[pid]['qty'] > 1:
                            st.session_state.cart[pid]['qty'] -= 1
                        else:
                            del st.session_state.cart[pid]
                        st.rerun()
                with q2:
                    st.markdown(f'<div class="qty-display">{item["qty"]}</div>', unsafe_allow_html=True)
                with q3:
                    if st.button("+", key=f"inc_{pid}", use_container_width=True):
                        st.session_state.cart[pid]['qty'] += 1
                        st.rerun()
                
                # Divider line
                st.markdown('<div style="height: 1px; background: #E8DCC8; margin: 0.75rem 0;"></div>', unsafe_allow_html=True)

        # Total and Checkout
        total = cart_total()
        st.markdown(f"""
        <div style="margin-top: 1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; padding:1rem; background:#FAF7F2; border-radius:12px;">
                <span style="font-family:'Playfair Display',serif; font-size:1.3rem; font-weight:700; color:#3C2415;">Total</span>
                <span style="font-family:'Playfair Display',serif; font-size:1.8rem; font-weight:700; color:#8A9A7B;">${total:.2f}</span>
            </div>
            <div style="text-align:center; color:#6B5444; margin:0.75rem 0;">{cart_count()} items</div>
        </div>
        """, unsafe_allow_html=True)

        col_clear, col_pay = st.columns(2)
        with col_clear:
            if st.button("🗑 Clear", use_container_width=True, type="secondary"):
                st.session_state.cart = {}
                st.rerun()
        with col_pay:
            if st.button("💳 Pay Now", use_container_width=True, type="primary"):
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                store = st.session_state.get('store', 'Gadong')
                items = []
                for pid, item in st.session_state.cart.items():
                    for _ in range(item['qty']):
                        conn.execute("INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?,?,?,?,?,?)",
                                     (int(pid), store, 1, item['price'], item['price'], ts))
                        items.append({'name': item['name'], 'price': item['price']})
                conn.commit()
                st.session_state.update({'last_order': {'items': items, 'total': total}, 'sale_done': True})
                st.rerun()
    else:
        st.markdown('<div style="text-align:center; padding:2rem; color:#6B5444;"><div style="font-size:3rem;">🛒</div><p>Your cart is empty</p><p style="font-size:0.875rem; color:#8A9A7B;">Tap products to add</p></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

conn.close()