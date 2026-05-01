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
    
    return df

def train_all_models():
    """Train one Prophet model per product per store. Returns count of models trained."""
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
            
            # Add lagged features as regressors
            if 'y_lag_1' in product_df.columns:
                product_df['lag_1'] = product_df['y_lag_1']
                product_df['lag_7'] = product_df['y_lag_7']
            else:
                product_df['lag_1'] = product_df['y'].shift(1).fillna(product_df['y'])
                product_df['lag_7'] = product_df['y'].shift(7).fillna(product_df['y'])
            
            try:
                model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=False,
                    changepoint_prior_scale=0.05,
                    interval_width=0.8,
                )
                model.add_regressor('lag_1')
                model.add_regressor('lag_7')
                model.fit(product_df)
                
                model_name = f"{store}_{product}".replace(" ", "_").lower()
                with open(os.path.join(MODELS_DIR, f"{model_name}.pkl"), 'wb') as f:
                    pickle.dump(model, f)
                
                models_trained += 1
            except Exception as e:
                print(f"Could not train: {store} - {product}: {e}")
    
    return models_trained

def generate_forecast(target_date=None):
    """Generate forecast for a specific date. Defaults to tomorrow."""
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
            
            if not os.path.exists(model_path):
                mask = (df['store'] == store) & (df['product'] == product)
                recent = df[mask].tail(7)
                if len(recent) > 0:
                    avg = round(recent['y'].mean())
                    results.append({
                        'store': store,
                        'product': product,
                        'recommended': avg,
                        'confidence': 'Low',
                        'lower_bound': max(0, avg - 10),
                        'upper_bound': avg + 10,
                    })
                continue
            
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                
                    future = model.make_future_dataframe(periods=30)
                    
                    # Add lag features for prediction
                    last_known = product_df[product_df['ds'] <= pd.to_datetime(target_date)].tail(7)
                    if len(last_known) >= 1:
                        future['lag_1'] = last_known['y'].iloc[-1] if len(last_known) >= 1 else product_df['y'].mean()
                    if len(last_known) >= 7:
                        future['lag_7'] = last_known['y'].iloc[-7] if len(last_known) >= 7 else product_df['y'].mean()
                    future['lag_1'] = future['lag_1'].fillna(product_df['y'].mean())
                    future['lag_7'] = future['lag_7'].fillna(product_df['y'].mean())
                    
                    forecast = model.predict(future)
                
                forecast['ds'] = forecast['ds'].dt.strftime("%Y-%m-%d")
                match = forecast[forecast['ds'] == target_date]
                
                if match.empty:
                    continue
                
                row = match.iloc[0]
                yhat = max(0, round(row['yhat']))
                yhat_lower = max(0, round(row['yhat_lower']))
                yhat_upper = round(row['yhat_upper'])
                
                interval_width = yhat_upper - yhat_lower
                if yhat > 0 and interval_width / yhat < 0.5:
                    conf = 'High'
                elif yhat > 0 and interval_width / yhat < 1.0:
                    conf = 'Medium'
                else:
                    conf = 'Low'
                
                results.append({
                    'store': store,
                    'product': product,
                    'recommended': yhat,
                    'confidence': conf,
                    'lower_bound': yhat_lower,
                    'upper_bound': yhat_upper,
                })
            except Exception as e:
                print(f"Forecast failed: {store} - {product}: {e}")
    
    return results

def save_forecast_to_db(forecast_results, target_date=None):
    """Save a generated forecast to the production_plans table."""
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
        if product_id:
            conn.execute(
                "INSERT INTO plan_items (plan_id, product_id, ai_recommended) VALUES (?, ?, ?)",
                (plan_id, product_id, item['recommended'])
            )
    
    conn.commit()
    conn.close()
    return plan_id