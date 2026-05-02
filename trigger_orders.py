import sqlite3

conn = sqlite3.connect('bakery.db')

# 1. Set target stock levels
conn.executemany('UPDATE ingredients SET target_stock=?, cost_per_unit=0.005 WHERE name=?', [
    (3000, 'Flour'), 
    (1500, 'Butter'), 
    (800, 'Sugar')
])

# 2. Check existing plans
plans_count = conn.execute('SELECT count(*) FROM production_plans').fetchone()[0]
print(f"Current plans: {plans_count}")

# 3. Add 7 days of production plans (25 units/day)
if plans_count == 0:
    prod = conn.execute('SELECT id FROM products LIMIT 1').fetchone()
    if prod:
        for i in range(1, 8):
            conn.execute("""
                INSERT INTO production_plans (product_id, quantity, scheduled_date)
                VALUES (?, 25, date('now', '+' || ? || ' days'))
            """, (prod[0], i))
        conn.commit()
        print("✅ Added 7 days of production plans (25 units/day)")
    else:
        print("⚠️ No products found. Add products first.")
else:
    print("ℹ️ Plans already exist. Skipping.")

# 4. Show current stock
print("\n📊 Current Stock Levels:")
for row in conn.execute("SELECT name, current_stock, target_stock FROM ingredients"):
    print(f"  {row[0]}: {row[1]}g (Target: {row[2]}g)")

conn.close()
print("\n✅ Done! Refresh the Ordering tab.")