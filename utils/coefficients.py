import sqlite3
from datetime import datetime, timedelta
from db import get_db

def calculate_monthly_coefficients(month=None):
    """
    Runs once per month. Calculates actual vs theoretical usage.
    Returns list of saved coefficients.
    """
    if month is None:
        month = (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
    
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all ingredients used in production this month
    cursor.execute("""
        SELECT ingredient_id, 
               SUM(quantity) as actual_usage_grams
        FROM inventory_transactions 
        WHERE type = 'production' 
          AND created_at LIKE ? || '%'
        GROUP BY ingredient_id
    """, (month,))
    actual_usage = {row["ingredient_id"]: row["actual_usage_grams"] for row in cursor.fetchall()}

    # Calculate theoretical usage per product-ingredient pair
    cursor.execute("""
        SELECT p.product_id, p.ingredient_id, p.coefficient_grams,
               SUM(r.quantity_baked) as total_baked
        FROM recipes p
        JOIN production_runs r ON p.product_id = r.product_id
        WHERE r.status = 'completed' AND r.completed_at LIKE ? || '%'
        GROUP BY p.product_id, p.ingredient_id
    """, (month,))
    theoretical_data = cursor.fetchall()

    new_coeffs = []
    for row in theoretical_data:
        prod_id = row["product_id"]
        ing_id = row["ingredient_id"]
        recipe_coeff = row["coefficient_grams"]
        total_baked = row["total_baked"]
        
        theoretical_total = recipe_coeff * total_baked
        actual_total = actual_usage.get(ing_id, 0)
        
        if theoretical_total == 0 or actual_total == 0:
            continue  # Skip if no data
            
        # Calculate raw coefficient
        raw_coeff = actual_total / theoretical_total
        
        # Confidence based on data points (more baked = higher confidence)
        confidence = min(1.0, total_baked / 50)  # caps at 50 units baked
        
        # Outlier protection: clamp between 0.85 and 1.25
        clamped_coeff = max(0.85, min(1.25, raw_coeff))
        
        # Smooth with existing coefficient if available
        cursor.execute("""
            SELECT coefficient FROM monthly_usage_coeffs 
            WHERE product_id=? AND ingredient_id=? AND month != ?
            ORDER BY created_at DESC LIMIT 1
        """, (prod_id, ing_id, month))
        prev_row = cursor.fetchone()
        
        if prev_row:
            # Weighted average: 70% new data, 30% historical trend
            final_coeff = (clamped_coeff * 0.7) + (prev_row["coefficient"] * 0.3)
        else:
            final_coeff = clamped_coeff

        # Upsert
        cursor.execute("""
            INSERT OR REPLACE INTO monthly_usage_coeffs 
            (product_id, ingredient_id, month, coefficient, confidence, data_points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (prod_id, ing_id, month, round(final_coeff, 3), round(confidence, 2), int(total_baked)))
        
        new_coeffs.append({
            "product_id": prod_id,
            "ingredient_id": ing_id,
            "month": month,
            "coefficient": final_coeff,
            "confidence": confidence
        })

    conn.commit()
    conn.close()
    return new_coeffs