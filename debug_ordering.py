import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('bakery.db')
conn.row_factory = sqlite3.Row

print("🔍 DIAGNOSTIC REPORT")
print("="*50)

# 1. Check Ingredients
print("\n📦 INGREDIENTS:")
for ing in conn.execute("SELECT name, current_stock, target_stock, cost_per_unit FROM ingredients"):
    print(f"  {ing['name']}: Stock={ing['current_stock']}g | Target={ing['target_stock']}g | Cost=${ing['cost_per_unit']}")

# 2. Check Production Plans
print("\n📅 PRODUCTION PLANS (Next 7 Days):")
target_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
plans = conn.execute("""
    SELECT COUNT(*), SUM(quantity) as total_qty
    FROM production_plans 
    WHERE scheduled_date BETWEEN date('now') AND ?
""", (target_date,)).fetchone()
print(f"  Total Plans: {plans[0]} | Total Units: {plans[1]}")

# 3. Check Recipes
print("\n📝 RECIPES:")
for r in conn.execute("""
    SELECT p.name as product, i.name as ingredient, r.coefficient_grams 
    FROM recipes r 
    JOIN products p ON r.product_id = p.id 
    JOIN ingredients i ON r.ingredient_id = i.id
    LIMIT 5
"""):
    print(f"  {r['product']} needs {r['coefficient_grams']}g of {r['ingredient']}")

# 4. Check Monthly Coefficients
print("\n📊 VARIANCE COEFFICIENTS:")
month = datetime.now().strftime("%Y-%m")
for c in conn.execute("""
    SELECT i.name, c.coefficient, c.confidence 
    FROM monthly_usage_coeffs c 
    JOIN ingredients i ON c.ingredient_id = i.id 
    WHERE c.month = ?
""", (month,)):
    print(f"  {c['name']}: Coeff={c['coefficient']} ({int((c['coefficient']-1)*100)}%) | Conf={c['confidence']}")

# 5. Manual Calculation for Flour
print("\n🧮 MANUAL CALCULATION (Flour):")
flour = conn.execute("SELECT * FROM ingredients WHERE name='Flour'").fetchone()
if flour:
    forecast = conn.execute(f"""
        SELECT COALESCE(SUM(pp.quantity), 0) FROM production_plans pp
        WHERE pp.scheduled_date BETWEEN date('now') AND '{target_date}'
    """).fetchone()[0]
    
    recipe = conn.execute("""
        SELECT COALESCE(AVG(coefficient_grams), 0) FROM recipes WHERE ingredient_id = ?
    """, (flour['id'],)).fetchone()[0]
    
    coeff_row = conn.execute("""
        SELECT coefficient FROM monthly_usage_coeffs 
        WHERE ingredient_id=? AND month=?
    """, (flour['id'], month)).fetchone()
    coeff = coeff_row['coefficient'] if coeff_row else 1.0
    
    need = forecast * recipe * coeff
    buffer = need * 0.15
    total_need = need + buffer
    shortfall = total_need - flour['current_stock']
    
    print(f"  Forecast: {forecast} units")
    print(f"  Recipe: {recipe}g/unit")
    print(f"  Variance Coeff: {coeff}")
    print(f"  Theoretical Need: {need}g")
    print(f"  Buffer (15%): {buffer}g")
    print(f"  Total Need: {total_need}g")
    print(f"  Current Stock: {flour['current_stock']}g")
    print(f"  SHORTFALL: {shortfall}g {'✅ ORDER NEEDED' if shortfall > 0 else '❌ NO ORDER'}")

conn.close()