import streamlit as st
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="Bakery Dashboard", layout="wide")
st.title("📊 Bakery AI Dashboard")

# ---- DEBUG: Direct database check ----
st.subheader("🔍 Database Debug")

try:
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    # Check sales count
    sales_count = conn.execute("SELECT COUNT(*) as cnt FROM sales").fetchone()
    st.write(f"Sales rows in DB: **{sales_count['cnt']}**")
    
    # Show last 5 sales
    last_sales = conn.execute("""
        SELECT timestamp, store, p.name, quantity, total 
        FROM sales s 
        JOIN products p ON s.product_id = p.id 
        ORDER BY s.id DESC LIMIT 5
    """).fetchall()
    
    if last_sales:
        st.write("**Last 5 sales:**")
        for s in last_sales:
            st.write(f"{s['timestamp']} | {s['store']} | {s['name']} x{s['quantity']} = ${s['total']:.2f}")
    else:
        st.write("No sales found.")
    
    # Check forecast
    plans = conn.execute("SELECT COUNT(*) as cnt FROM production_plans").fetchone()
    st.write(f"Production plans: **{plans['cnt']}**")
    
    if plans['cnt'] > 0:
        latest = conn.execute("""
            SELECT pp.date, COUNT(pi.id) as items
            FROM production_plans pp
            LEFT JOIN plan_items pi ON pp.id = pi.plan_id
            GROUP BY pp.id
            ORDER BY pp.id DESC LIMIT 1
        """).fetchone()
        st.write(f"Latest plan: **{latest['date']}** with {latest['items']} items")
    
    conn.close()
    
except Exception as e:
    st.error(f"Database error: {e}")

# ---- END DEBUG ----