import sqlite3
conn = sqlite3.connect('bakery.db')

# 1. Set target stock levels (triggers reorder logic when stock drops below this)
conn.executemany('UPDATE ingredients SET target_stock=?, cost_per_unit=0.005, lead_time_days=2 WHERE name=?', [
    (3000, 'Flour'), (1500, 'Butter'), (800, 'Sugar')
])

# 2. Inject 7 days of production plans (25 units/day) if empty
plans_count = conn.execute('SELECT count(*) FROM production_plans').fetchone()[0]
if plans_count == 0:
    prod = conn.execute('SELECT id FROM products LIMIT 1').fetchone()
    if prod:
        conn.executemany(
            'INSERT INTO production_plans (product_id, quantity, scheduled_date) VALUES (?, ?, date("now", "+" || ? || " days"))', 
            [(prod[0], 25, i) for i in range(1, 8)]
        )

conn.commit()
conn.close()
print('✅ Data updated. Refresh the Ordering tab.')