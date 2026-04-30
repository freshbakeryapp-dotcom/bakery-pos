"""Run this via cron at 3am daily. Retrains all models and saves forecast."""
from engine import train_all_models, generate_forecast, save_forecast_to_db
from datetime import datetime

print(f"[{datetime.now()}] Starting nightly training...")
count = train_all_models()
print(f"[{datetime.now()}] Trained {count} models.")

if count > 0:
    forecast = generate_forecast()
    if forecast:
        plan_id = save_forecast_to_db(forecast)
        print(f"[{datetime.now()}] Forecast saved. Plan ID: {plan_id}")
    else:
        print(f"[{datetime.now()}] No forecast generated.")
else:
    print(f"[{datetime.now()}] Not enough data to train.")

print(f"[{datetime.now()}] Done.")