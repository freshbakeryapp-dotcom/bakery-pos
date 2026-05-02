import sqlite3
from datetime import datetime, timedelta
from db import get_db

conn = get_db()

# 1. Add dummy ingredients
conn.executemany("INSERT OR IGNORE INTO ingredients (name, unit, current_stock) VALUES (?, ?, ?)", [
    ("Flour", "g", 5000), ("Butter", "g", 2000), ("Sugar", "g", 1000)
])

# 2. Add dummy recipes (Croissant = 100g flour, 50g butter, 10g sugar)
products = conn.execute("SELECT id FROM products LIMIT 3").fetchall()
if products:
    pid = products[0]["id"]
    conn.executemany("INSERT OR IGNORE INTO recipes (product_id, ingredient_id, coefficient_grams) VALUES (?, ?, ?)", [
        (pid, 1, 100), (pid, 2, 50), (pid, 3, 10)
    ])

    # 3. Simulate 60 baked croissants this month
    conn.execute("""
        INSERT INTO production_runs (product_id, quantity_baked, status, completed_at)
        VALUES (?, ?, 'completed', ?)
    """, (pid, 60, datetime.now().strftime("%Y-%m-%d")))

    # 4. Log actual usage (simulating +8% real-world variance)
    conn.executemany("INSERT INTO inventory_transactions (ingredient_id, type, quantity) VALUES (?, 'production', ?)", [
        (1, -6480),  # 100g * 60 * 1.08
        (2, -3240),  # 50g * 60 * 1.08
        (3, -648)    # 10g * 60 * 1.08
    ])

conn.commit()
conn.close()
print("✅ Dummy data injected. Refresh your app.")