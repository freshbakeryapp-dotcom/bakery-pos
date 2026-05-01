import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

products = conn.execute("SELECT id, name, price FROM products").fetchall()
stores = ["Gadong", "Kiulap", "Seria", "Kuala Belait", "Tutong", "Batu Satu", "Sengkurong"]

# Generate 60 days of sales starting from 60 days ago
for days_ago in range(60, 0, -1):
    date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    
    for store in random.sample(stores, 3):
        for product in products:
            if store in ["Gadong", "Kiulap"]:
                qty = random.randint(25, 70)
            elif store in ["Seria", "Kuala Belait"]:
                qty = random.randint(15, 45)
            else:
                qty = random.randint(8, 30)
            
            timestamp = f"{date} {random.randint(7,19):02d}:{random.randint(0,59):02d}:00"
            
            conn.execute(
                "INSERT INTO sales (product_id, store, quantity, unit_price, total, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (product['id'], store, qty, product['price'], qty * product['price'], timestamp)
            )

conn.commit()
conn.close()
print("✅ 60 days of multi-date sales seeded.")