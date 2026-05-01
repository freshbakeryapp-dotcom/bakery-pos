import streamlit as st
import sqlite3
from db import get_db, init_db

init_db()

st.set_page_config(page_title="Product Management", layout="wide")
st.title("📦 Product Management")

conn = get_db()

tab1, tab2 = st.tabs(["📋 All Products", "➕ Add Product"])

with tab1:
    products = conn.execute("SELECT * FROM products ORDER BY category, name").fetchall()
    
    if products:
        st.write(f"**{len(products)} products**")
        
        for product in products:
            with st.expander(f"{product['name']} — ${product['price']:.2f} ({product['category']})"):
                col1, col2, col3 = st.columns(3)
                
                new_name = col1.text_input("Name", value=product['name'], key=f"name_{product['id']}")
                new_category = col2.text_input("Category", value=product['category'] or "", key=f"cat_{product['id']}")
                new_price = col3.number_input("Price ($)", value=float(product['price']), min_value=0.0, step=0.50, key=f"price_{product['id']}")
                
                col4, col5 = st.columns(2)
                new_cost = col4.number_input("Cost to make ($)", value=float(product['cost_to_make'] or 0), min_value=0.0, step=0.10, key=f"cost_{product['id']}")
                new_shelf = col5.number_input("Shelf life (hours)", value=int(product['shelf_life_hours'] or 24), min_value=1, max_value=168, step=1, key=f"shelf_{product['id']}")
                
                col6, col7 = st.columns(2)
                if col6.button("💾 Update", key=f"update_{product['id']}"):
                    conn.execute(
                        "UPDATE products SET name=?, category=?, price=?, cost_to_make=?, shelf_life_hours=? WHERE id=?",
                        (new_name, new_category, new_price, new_cost, new_shelf, product['id'])
                    )
                    conn.commit()
                    st.success(f"✅ {new_name} updated!")
                    st.rerun()
                
                if col7.button("🗑️ Delete", key=f"delete_{product['id']}"):
                    sales_count = conn.execute(
                        "SELECT COUNT(*) as cnt FROM sales WHERE product_id = ?",
                        (product['id'],)
                    ).fetchone()['cnt']
                    
                    if sales_count > 0:
                        st.warning(f"Cannot delete — has {sales_count} sales records.")
                    else:
                        conn.execute("DELETE FROM products WHERE id = ?", (product['id'],))
                        conn.commit()
                        st.success(f"🗑️ {product['name']} deleted.")
                        st.rerun()
    else:
        st.info("No products found.")

with tab2:
    st.subheader("Add New Product")
    
    # Use a form so it clears on submit
    with st.form("add_product_form", clear_on_submit=True):
        cols = st.columns(2)
        add_name = cols[0].text_input("Product Name")
        add_category = cols[1].text_input("Category (e.g., Bread, Pastry, Local)")
        
        cols2 = st.columns(3)
        add_price = cols2[0].number_input("Selling Price ($)", min_value=0.0, step=0.50)
        add_cost = cols2[1].number_input("Cost to Make ($)", min_value=0.0, step=0.10)
        add_shelf = cols2[2].number_input("Shelf Life (hours)", min_value=1, max_value=168, value=24, step=1)
        
        submitted = st.form_submit_button("➕ Add Product", type="primary")
        
        if submitted:
            if add_name and add_price > 0:
                conn.execute(
                    "INSERT INTO products (name, category, price, cost_to_make, shelf_life_hours) VALUES (?, ?, ?, ?, ?)",
                    (add_name, add_category, add_price, add_cost, add_shelf)
                )
                conn.commit()
                st.success(f"✅ {add_name} added!")
                st.balloons()
                st.rerun()
            else:
                st.error("Product name and price are required.")

conn.close()