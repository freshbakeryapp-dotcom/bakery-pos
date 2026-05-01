import sqlite3
import pandas as pd
from prophet import Prophet
import pickle
import os
from datetime import datetime, timedelta

MODELS_DIR = "models"

def get_sales_data():
    """Pull all sales from database with feature engineering."""
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    df = pd.read_sql_query("""
        SELECT 
            date(timestamp) as ds,
            store,
            p.name as product,
            SUM(quantity) as y
        FROM sales s
        JOIN products p ON s.product_id = p.id
        GROUP BY date(timestamp), store, p.name
        ORDER BY ds
    """, conn)
    conn.close()
    
    if df.empty:
        return df
    
    # Feature engineering
    from src.features import engineer_features
    df = engineer_features(df)
    
    # Add weather
    from src.weather import merge_weather_with_sales
    df = merge_weather_with_sales(df)
    
    return df


def train_all_models():
    """Train one Prophet model per product per store."""
    df = get_sales_data()
    
    if df.empty:
        return 0
    
    os.makedirs(MODELS_DIR, exist_ok=True)
    models_trained = 0
    
    for store in df['store'].unique():
        for product in df['product'].unique():
            mask = (df['store'] == store) & (df['product'] == product)
            product_df = df[mask][['ds', 'y']].copy()
            
            if len(product_df) < 3:
                continue
            
            product_df['ds'] = pd.to_datetime(product_df['ds'])
            
            try:
                model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=False,
                    changepoint_prior_scale=0.05,
                    interval_width=0.8,
                )
                
                # Add weather regressor if available
                has_weather = 'precipitation_mm' in product_df.columns and product_df['precipitation_mm'].notna().any()
                if has_weather:
                    model.add_regressor('precipitation_mm')
                
                model.fit(product_df[['ds', 'y'] + (['precipitation_mm'] if has_weather else [])])
                
                model_name = f"{store}_{product}".replace(" ", "_").lower()
                with open(os.path.join(MODELS_DIR, f"{model_name}.pkl"), 'wb') as f:
                    pickle.dump(model, f)
                
                models_trained += 1
            except Exception as e:
                print(f"Could not train: {store} - {product}: {e}")
    
    return models_trained


def generate_forecast(target_date=None):
    """Generate forecast. Uses historical average as fallback."""
    if target_date is None:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    df = get_sales_data()
    
    if df.empty:
        return []
    
    results = []
    
    for store in df['store'].unique():
        for product in df['product'].unique():
            model_name = f"{store}_{product}".replace(" ", "_").lower()
            model_path = os.path.join(MODELS_DIR, f"{model_name}.pkl")
            
            yhat = None
            yhat_lower = None
            yhat_upper = None
            conf = 'Low'
            
            # Try model
            if os.path.exists(model_path):
                try:
                    with open(model_path, 'rb') as f:
                        model = pickle.load(f)
                    
                    future = model.make_future_dataframe(periods=30)
                    
                    # Add weather to future dates if model expects it
                    from src.weather import get_weather_for_period
                    future_dates = pd.Series(pd.to_datetime(future['ds'].unique()))
                    weather_future = get_weather_for_period(future_dates)
                    
                    if not weather_future.empty and 'precipitation_mm' in weather_future.columns:
                        weather_future['date'] = pd.to_datetime(weather_future['date'])
                        future['ds_date'] = pd.to_datetime(future['ds'])
                        future = future.merge(
                            weather_future[['date', 'precipitation_mm']],
                            left_on='ds_date', right_on='date', how='left'
                        )
                        future['precipitation_mm'] = future['precipitation_mm'].fillna(0)
                        future = future.drop(columns=['ds_date', 'date'], errors='ignore')
                    
                    forecast = model.predict(future)
                    
                    forecast['ds'] = forecast['ds'].dt.strftime("%Y-%m-%d")
                    match = forecast[forecast['ds'] == target_date]
                    
                    if not match.empty:
                        row = match.iloc[0]
                        yhat = max(0, round(row['yhat']))
                        yhat_lower = max(0, round(row['yhat_lower']))
                        yhat_upper = round(row['yhat_upper'])
                        
                        if yhat > 0:
                            interval_width = yhat_upper - yhat_lower
                            ratio = interval_width / yhat
                            if ratio < 0.3:
                                conf = 'High'
                            elif ratio < 0.7:
                                conf = 'Medium'
                except Exception as e:
                    print(f"Model failed for {model_name}: {e}")
            
            # Fallback: historical average
            if yhat is None:
                mask = (df['store'] == store) & (df['product'] == product)
                recent = df[mask].tail(7)
                if len(recent) > 0:
                    yhat = round(recent['y'].mean())
                    yhat_lower = max(0, yhat - 10)
                    yhat_upper = yhat + 10
                else:
                    continue
            
            results.append({
                'store': store,
                'product': product,
                'recommended': yhat,
                'confidence': conf,
                'lower_bound': yhat_lower or max(0, yhat - 10),
                'upper_bound': yhat_upper or yhat + 10,
            })
    
    return results


def save_forecast_to_db(forecast_results, target_date=None):
    """Save forecast to production_plans table."""
    if target_date is None:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(
        "INSERT INTO production_plans (store, date, created_at) VALUES (?, ?, ?)",
        ("All", target_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    plan_id = cursor.lastrowid
    
    product_map = {}
    for row in conn.execute("SELECT id, name FROM products"):
        product_map[row['name'].lower()] = row['id']
    
    for item in forecast_results:
        product_id = product_map.get(item['product'].lower())
        if not product_id:
            # Try case-insensitive match
            for name, pid in product_map.items():
                if name.lower() == item['product'].lower():
                    product_id = pid
                    break
        
        if product_id:
            conn.execute(
                "INSERT INTO plan_items (plan_id, product_id, ai_recommended) VALUES (?, ?, ?)",
                (plan_id, product_id, item['recommended'])
            )
    
    conn.commit()
    conn.close()
    return plan_id