"""
Feature engineering for bakery forecasting.
Handles stockout detection, synthetic demand, and lagged features.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def detect_stockouts(df):
    """
    Flag days where sales likely hit capacity (sold out).
    Requires columns: ds, y, bake_plan
    If bake_plan is not available, uses a heuristic: 
    sales > 90th percentile for that product-store = likely stockout.
    """
    df = df.copy()
    df['is_capped'] = False
    
    if 'bake_plan' in df.columns:
        # Direct: if sales >= bake plan, they sold everything they baked
        df['is_capped'] = df['y'] >= df['bake_plan']
    else:
        # Heuristic: sales in top 10% of all sales for this product-store
        for (store, product), group in df.groupby(['store', 'product']):
            threshold = group['y'].quantile(0.90)
            df.loc[(df['store'] == store) & (df['product'] == product) & (df['y'] >= threshold), 'is_capped'] = True
    
    return df


def apply_synthetic_demand(df):
    """
    Replace capped sales with 3-week rolling average of same weekday.
    This estimates true demand on days they sold out.
    """
    df = df.copy()
    df['y_original'] = df['y']
    df['y_synthetic'] = df['y']
    
    for (store, product), group in df.groupby(['store', 'product']):
        group = group.sort_values('ds')
        group = group.set_index('ds')
        
        # 3-week rolling average (same weekday = 7-day intervals)
        group['rolling_3w'] = group['y'].rolling(window=3, min_periods=1).mean()
        
        # For capped days, use the rolling average
        mask = group['is_capped']
        group.loc[mask, 'y_synthetic'] = group.loc[mask, 'rolling_3w'].round(0)
        
        # Update back to df
        for idx in group.index:
            df.loc[(df['store'] == store) & (df['product'] == product) & (df['ds'] == idx), 'y_synthetic'] = group.loc[idx, 'y_synthetic']
    
    # Use synthetic y as the target for training
    df['y'] = df['y_synthetic']
    
    return df


def add_lagged_features(df):
    """
    Add T-1 (yesterday) and T-7 (same day last week) as features.
    These capture immediate momentum and weekly patterns.
    """
    df = df.copy()
    df['y_lag_1'] = np.nan
    df['y_lag_7'] = np.nan
    
    for (store, product), group in df.groupby(['store', 'product']):
        group = group.sort_values('ds')
        
        group['y_lag_1'] = group['y'].shift(1)
        group['y_lag_7'] = group['y'].shift(7)
        
        for idx in group.index:
            df.loc[(df['store'] == store) & (df['product'] == product) & (df['ds'] == idx), 'y_lag_1'] = group.loc[idx, 'y_lag_1']
            df.loc[(df['store'] == store) & (df['product'] == product) & (df['ds'] == idx), 'y_lag_7'] = group.loc[idx, 'y_lag_7']
    
    # Fill NaN lags with the mean for that product
    df['y_lag_1'] = df['y_lag_1'].fillna(df['y'])
    df['y_lag_7'] = df['y_lag_7'].fillna(df['y'])
    
    return df


def engineer_features(df):
    """
    Full feature engineering pipeline.
    Returns df with is_capped, y_synthetic, y_lag_1, y_lag_7.
    """
    df = detect_stockouts(df)
    df = apply_synthetic_demand(df)
    df = add_lagged_features(df)
    
    return df


def calculate_stockout_penalty(actual_bake, actual_sales, ai_recommendation):
    """
    Calculate asymmetric penalty for model evaluation.
    Stockout penalty (under-baked): lost revenue = (demand - baked) * price
    Waste penalty (over-baked): cost of wasted goods = (baked - sold) * cost
    
    Returns dict with penalties.
    """
    if actual_sales >= actual_bake:
        # Stockout: they could have sold more
        estimated_lost_sales = max(0, actual_sales - ai_recommendation)
        penalty = estimated_lost_sales * 2  # Stockouts hurt more than waste
        penalty_type = 'stockout'
    else:
        # Overproduction: wasted goods
        waste = actual_bake - actual_sales
        penalty = waste
        penalty_type = 'waste'
    
    return {
        'penalty_type': penalty_type,
        'penalty_units': penalty,
        'ai_recommendation': ai_recommendation,
        'actual_bake': actual_bake,
        'actual_sales': actual_sales
    }