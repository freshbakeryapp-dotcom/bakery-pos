"""A tiny API endpoint to trigger training via HTTP."""
from flask import Flask, jsonify
from engine import train_all_models, generate_forecast, save_forecast_to_db

app = Flask(__name__)

@app.route("/train", methods=["POST", "GET"])
def train():
    count = train_all_models()
    if count == 0:
        return jsonify({"status": "error", "message": "Not enough data", "models_trained": 0})
    
    forecast = generate_forecast()
    plan_id = save_forecast_to_db(forecast)
    
    return jsonify({
        "status": "success",
        "models_trained": count,
        "plan_id": plan_id,
        "forecast_items": len(forecast)
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)