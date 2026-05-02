import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from db import get_db

st.set_page_config(page_title="Dashboard - Artisan Crumb", layout="wide")

conn = get_db()

# Helper: Get sales data
def get_sales_data(days=30):
    query = """
        SELECT 
            s.timestamp,
            p.name as product_name,
            p.category,
            s.store,
            s.quantity,
            s.unit_price,
            s.total
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.timestamp >= datetime('now', '-{} days')
        ORDER BY s.timestamp DESC
    """.format(days)
    return pd.read_sql_query(query, conn)

# Helper: Simple forecast WITHOUT weather regressors (fallback)
def simple_forecast(df, product_name, days_ahead=7):
    """Simple moving average forecast - no external dependencies"""
    if df.empty:
        return None
    
    # Aggregate daily sales
    daily = df.groupby(df['timestamp'].dt.date)['quantity'].sum().reset_index()
    daily.columns = ['ds', 'y']
    daily['ds'] = pd.to_datetime(daily['ds'])
    
    if len(daily) < 7:
        return None  # Not enough data
    
    # Calculate 7-day moving average
    daily['ma7'] = daily['y'].rolling(window=7, min_periods=1).mean()
    
    # Forecast: use last MA value
    last_ma = daily['ma7'].iloc[-1]
    future_dates = pd.date_range(start=daily['ds'].iloc[-1] + timedelta(days=1), periods=days_ahead, freq='D')
    
    # Create forecast dataframe with ONLY the 'y' column for charting
    # We don't plot 'type' to avoid color errors
    forecast = pd.DataFrame({
        'ds': future_dates,
        'y': [last_ma] * days_ahead
    })
    
    return forecast, daily

# Helper: Get top products
def get_top_products(limit=5):
    query = """
        SELECT 
            p.name,
            p.category,
            SUM(s.quantity) as total_sold,
            SUM(s.total) as revenue
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY p.id, p.name, p.category
        ORDER BY total_sold DESC
        LIMIT ?
    """
    return pd.read_sql_query(query, conn, params=(limit,))

# Header
st.markdown('<h1 style="font-family: \'Playfair Display\', serif; color: #3C2415;">📊 Dashboard</h1>', unsafe_allow_html=True)
st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

# Store selector
store = st.selectbox(
    "Filter by Store",
    ["All Stores", "Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"],
    index=0
)

# Load data
with st.spinner("Loading sales data..."):
    df = get_sales_data(days=30)

if df.empty:
    st.warning("📦 No sales data found. Start making sales to see analytics!")
    conn.close()
    st.stop()

# Filter by store
if store != "All Stores":
    df = df[df['store'] == store]

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_sales = df['total'].sum()
    st.metric("💰 Total Revenue", f"${total_sales:,.2f}", delta=f"{len(df)} orders")
with col2:
    total_items = df['quantity'].sum()
    st.metric("🥐 Items Sold", f"{total_items:,}")
with col3:
    avg_ticket = df['total'].mean()
    st.metric("🧾 Avg. Order", f"${avg_ticket:.2f}")
with col4:
    unique_products = df['product_name'].nunique()
    st.metric("📦 Products", f"{unique_products}")

st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

# Top Products Chart
st.subheader("🏆 Top Selling Products")
top_products = get_top_products(limit=10)
if not top_products.empty:
    # Rename for better chart labels
    chart_data = top_products.rename(columns={'name': 'Product', 'total_sold': 'Quantity Sold'})
    st.bar_chart(chart_data.set_index('Product')['Quantity Sold'], color="#8A9A7B")
else:
    st.info("No product data available yet.")

st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

# Simple Forecast Section (Weather-Independent)
st.subheader("🔮 Demand Forecast (Next 7 Days)")

# Get unique products in filtered data
products = df['product_name'].unique()[:5]  # Limit to 5 for performance

if products.size > 0:
    selected_product = st.selectbox("Select product to forecast", products)
    
    product_df = df[df['product_name'] == selected_product].copy()
    product_df['timestamp'] = pd.to_datetime(product_df['timestamp'])
    
    result = simple_forecast(product_df, selected_product)
    
    if result:
        forecast_df, hist_df = result
        
        # Combine historical + forecast for charting
        # We only plot the 'y' column to avoid color length errors
        hist_plot = hist_df[['ds', 'y']].rename(columns={'ds': 'Date', 'y': 'Sales'})
        hist_plot['Type'] = 'Historical'
        
        forecast_plot = forecast_df[['ds', 'y']].rename(columns={'ds': 'Date', 'y': 'Sales'})
        forecast_plot['Type'] = 'Forecast'
        
        combined = pd.concat([hist_plot, forecast_plot], ignore_index=True)
        
        # Plot using Altair or just simple line chart with one color
        # To avoid the error, we plot the whole dataframe but specify ONE color for the main metric
        # Or we use altair for more control. Let's stick to simple st.line_chart for now.
        
        # Prepare data for st.line_chart: Index must be Date, Column must be Sales
        chart_ready = combined.set_index('Date')[['Sales']]
        
        st.line_chart(chart_ready, color="#8A9A7B")
        
        st.caption(f"Forecast based on 7-day moving average. Weather data unavailable.")
    else:
        st.info(f"📊 Not enough historical data for {selected_product} (need 7+ days)")
else:
    st.info("Select a store with sales data to see forecasts.")

st.markdown('<div style="height: 2rem;"></div>', unsafe_allow_html=True)

# Recent Sales Table
st.subheader("🕐 Recent Sales")
recent = df.head(20)[['timestamp', 'product_name', 'store', 'quantity', 'total']]
recent.columns = ['Time', 'Product', 'Store', 'Qty', 'Total']
st.dataframe(recent, use_container_width=True, hide_index=True)

conn.close()

# Footer note
st.markdown('<div style="margin-top: 3rem; text-align: center; color: #6B5444; font-size: 0.875rem;">', unsafe_allow_html=True)
st.markdown("💡 *Forecasting uses simple moving average. Weather integration requires API access.*")
st.markdown('</div>', unsafe_allow_html=True)