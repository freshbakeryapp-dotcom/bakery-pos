import sqlite3
conn = sqlite3.connect('bakery.db')

print("🔍 RECIPE CHECK:")
for row in conn.execute("""
    SELECT p.name as product, i.name as ingredient, r.coefficient_grams 
    FROM recipes r 
    JOIN products p ON r.product_id = p.id 
    JOIN ingredients i ON r.ingredient_id = i.id
"""):
    print(f"  {row[0]} needs {row[2]}g of {row[1]}")

print("\n📦 PRODUCTS WITHOUT RECIPES:")
for row in conn.execute("""
    SELECT p.name, p.id 
    FROM products p 
    LEFT JOIN recipes r ON p.id = r.product_id 
    WHERE r.id IS NULL
"""):
    print(f"  {row[0]} (ID: {row[1]})")

conn.close()