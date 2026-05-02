import sqlite3
conn = sqlite3.connect('bakery.db')

# 1. Create a production plan for today
conn.execute("""
    INSERT OR IGNORE INTO production_plans (store, date) 
    VALUES ('Gadong', date('now'))
""")
plan_id = conn.execute("SELECT id FROM production_plans ORDER BY id DESC LIMIT 1").fetchone()[0]

# 2. Get first product ID
prod = conn.execute("SELECT id FROM products LIMIT 1").fetchone()
if prod:
    pid = prod[0]
    # 3. Insert plan_items with AI recommended quantity (25/day for 7 days simulation)
    # We'll simulate 7 days by adding 7 plan entries
    for i in range(7):
        conn.execute("""
            INSERT INTO plan_items (plan_id, product_id, ai_recommended, baker_override)
            VALUES (?, ?, 25, 25)
        """, (plan_id, pid))
    
    # 4. Ensure target stocks are set
    conn.executemany('UPDATE ingredients SET target_stock=?, cost_per_unit=0.005 WHERE name=?', [
        (3000, 'Flour'), (1500, 'Butter'), (800, 'Sugar')
    ])
    conn.commit()
    print("✅ Valid plan injected: 175 units scheduled over next 7 days.")
else:
    print("⚠️ No products found.")
conn.close()