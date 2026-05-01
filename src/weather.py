"""
Weather integration for bakery forecasting.
Uses Open-Meteo free API (no key required).
"""
import pandas as pd
import requests
from datetime import datetime, timedelta
import sqlite3
import os
import json

CACHE_FILE = "data/weather_cache.json"

def get_brunei_coordinates():
    """Brunei coordinates (Bandar Seri Begawan area)."""
    return {"lat": 4.9031, "lon": 114.9398}


def fetch_historical_weather(start_date, end_date):
    """
    Fetch historical weather from Open-Meteo.
    Free, no API key needed.
    Returns DataFrame with date, precipitation, temp_max, is_rainy.
    """
    coords = get_brunei_coordinates()
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "daily": ["precipitation_sum", "temperature_2m_max"],
        "timezone": "Asia/Brunei"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "daily" not in data:
            return pd.DataFrame()
        
        df = pd.DataFrame({
            "date": pd.to_datetime(data["daily"]["time"]),
            "precipitation_mm": data["daily"]["precipitation_sum"],
            "temp_max_c": data["daily"]["temperature_2m_max"],
        })
        
        # Rainy day = any precipitation
        df["is_rainy"] = df["precipitation_mm"] > 0.5
        
        return df
    
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return pd.DataFrame()


def get_weather_for_period(dates):
    """
    Get weather for a list of dates.
    Uses cache to avoid repeated API calls.
    """
    if dates.empty:
        return pd.DataFrame()
    
    min_date = dates.min().strftime("%Y-%m-%d")
    max_date = dates.max().strftime("%Y-%m-%d")
    
    # Check cache
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        
        cache_min = cache.get("min_date", "")
        cache_max = cache.get("max_date", "")
        
        # If cache covers the range, use it
        if cache_min <= min_date and cache_max >= max_date:
            df = pd.DataFrame(cache["data"])
            df["date"] = pd.to_datetime(df["date"])
            return df
    
    # Fetch from API
    df = fetch_historical_weather(min_date, max_date)
    
    if not df.empty:
        # Save cache
        cache_data = {
            "min_date": min_date,
            "max_date": max_date,
            "data": df.to_dict(orient="records")
        }
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f, default=str)
    
    return df


def merge_weather_with_sales(sales_df):
    """
    Merge weather data with sales data.
    sales_df must have 'ds' column with dates.
    Returns sales_df with added weather columns.
    """
    if sales_df.empty:
        sales_df["precipitation_mm"] = 0
        sales_df["temp_max_c"] = 30
        sales_df["is_rainy"] = False
        return sales_df
    
    # Get unique dates from sales
    dates = pd.to_datetime(sales_df["ds"].unique())
    dates_series = pd.Series(dates)
    
    # Fetch weather
    weather_df = get_weather_for_period(dates_series)
    
    if weather_df.empty:
        sales_df["precipitation_mm"] = 0
        sales_df["temp_max_c"] = 30
        sales_df["is_rainy"] = False
        return sales_df
    
    # Merge
    sales_df["ds_date"] = pd.to_datetime(sales_df["ds"])
    weather_df["date"] = pd.to_datetime(weather_df["date"])
    
    sales_df = sales_df.merge(
        weather_df,
        left_on="ds_date",
        right_on="date",
        how="left"
    )
    
    # Fill missing
    sales_df["precipitation_mm"] = sales_df["precipitation_mm"].fillna(0)
    sales_df["temp_max_c"] = sales_df["temp_max_c"].fillna(30)
    sales_df["is_rainy"] = sales_df["is_rainy"].fillna(False)
    
    # Clean up
    sales_df = sales_df.drop(columns=["ds_date", "date"], errors="ignore")
    
    return sales_df


def add_weather_to_forecast(forecast_results, target_date):
    """
    Add weather context to forecast results.
    Fetches forecast for target date and adjusts confidence.
    """
    coords = get_brunei_coordinates()
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "daily": ["precipitation_sum"],
        "timezone": "Asia/Brunei",
        "start_date": target_date,
        "end_date": target_date
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if "daily" in data and len(data["daily"]["precipitation_sum"]) > 0:
            rain = data["daily"]["precipitation_sum"][0] or 0
            is_rainy = rain > 0.5
            
            for item in forecast_results:
                item["rain_mm"] = rain
                item["is_rainy"] = is_rainy
                
                if is_rainy and item["confidence"] == "High":
                    item["confidence"] = "Medium"
                    item["confidence_note"] = "Rain expected — foot traffic may be lower"
                elif is_rainy:
                    item["confidence_note"] = "Rain expected"
    
    except Exception as e:
        print(f"Forecast weather fetch failed: {e}")
        for item in forecast_results:
            item["rain_mm"] = 0
            item["is_rainy"] = False
    
    return forecast_results