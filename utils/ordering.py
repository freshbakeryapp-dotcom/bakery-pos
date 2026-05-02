import sqlite3
from datetime import datetime, timedelta
from db import get_db

def get_order_recommendations(days_ahead=7):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    ingredients = conn.execute("SELECT * FROM ingredients WHERE target_stock > 0").fetchall()
    recommendations = []
    current_month = datetime.now().strftime("%Y-%m")
    target_date = (datetime.now() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    for ing in ingredients:
        current_stock = ing["current_stock"]
        unit = ing["unit"]
        forecast_qty = 0
        
        # 🔍 CORRECTED: Query plan_items for approved/recommended quantities
        try:
            forecast_qty = conn.execute("""
                SELECT COALESCE(SUM(COALESCE(pi.baker_override, pi.ai_recommended, pi.p90_safe, 0)), 0)
                FROM plan_items pi
                JOIN production_plans pp ON pi.plan_id = pp.id
                WHERE pp.date BETWEEN date('now') AND ?
            """, (target_date,)).fetchone()[0]
        except Exception:
            pass

        # Fallback: Last month's actual production
        if forecast_qty == 0:
            try:
                daily_avg = conn.execute("""
                    SELECT COALESCE(SUM(quantity_baked), 0) / 30.0
                    FROM production_runs WHERE status='completed' AND completed_at LIKE ? || '%'
                """, (current_month,)).fetchone()[0]
                forecast_qty = daily_avg * days_ahead
            except Exception:
                forecast_qty = 0

        # 🧮 Calculation
        recipe_coeff = conn.execute("""
            SELECT COALESCE(AVG(coefficient_grams), 0) FROM recipes WHERE ingredient_id = ?
        """, (ing["id"],)).fetchone()[0]

        coeff_row = conn.execute("""
            SELECT coefficient, confidence FROM monthly_usage_coeffs 
            WHERE ingredient_id=? AND month=?
        """, (ing["id"], current_month)).fetchone()
        
        variance_coeff = coeff_row["coefficient"] if coeff_row else 1.0
        confidence = coeff_row["confidence"] if coeff_row else 0.0
        
        theoretical_need_grams = forecast_qty * recipe_coeff * variance_coeff
        need_qty = theoretical_need_grams  # Assumes grams
        
        buffer_pct = 0.15 + ((1 - confidence) * 0.10)
        total_need = need_qty * (1 + buffer_pct)
        shortfall = total_need - current_stock
        
        if shortfall > 0:
            recommendations.append({
                "id": ing["id"], "name": ing["name"], "unit": unit,
                "current_stock": round(current_stock, 1),
                "forecast_demand": round(forecast_qty, 1),
                "variance_coeff": variance_coeff,
                "confidence": round(confidence * 100),
                "recommended_order": round(shortfall, 1),
                "estimated_cost": round(shortfall * ing["cost_per_unit"], 2)
            })
            
    conn.close()
    return recommendations

def confirm_order(ingredient_id, quantity, cost):
    conn = get_db()
    conn.execute("UPDATE ingredients SET current_stock = current_stock + ? WHERE id = ?", (quantity, ingredient_id))
    conn.execute("""
        INSERT INTO inventory_transactions (ingredient_id, type, quantity, reference_id)
        VALUES (?, 'purchase', ?, ?)
    """, (ingredient_id, quantity, ingredient_id))
    conn.commit()
    conn.close()
    return True