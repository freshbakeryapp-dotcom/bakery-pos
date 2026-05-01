import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bakery.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            cost_to_make REAL,
            shelf_life_hours INTEGER DEFAULT 24
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            store TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS production_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            ai_recommended INTEGER NOT NULL,
            p90_safe INTEGER DEFAULT 0,
            baker_override INTEGER,
            actually_produced INTEGER,
            kitchen_accident INTEGER DEFAULT 0,
            damaged_dropped INTEGER DEFAULT 0,
            expired_stale INTEGER DEFAULT 0,
            other_loss INTEGER DEFAULT 0,
            actually_sold INTEGER,
            wasted INTEGER,
            waste_reason TEXT DEFAULT 'overproduction',
            FOREIGN KEY (plan_id) REFERENCES production_plans(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_item_id INTEGER NOT NULL,
            store TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT 'overproduction',
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (plan_item_id) REFERENCES plan_items(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store TEXT NOT NULL,
            date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            expected_impact TEXT DEFAULT 'medium',
            created_at TEXT NOT NULL
        )
    """)
    
    # Seed products if empty
    sample_products = [
        ("Sourdough Loaf", "Bread", 4.50, 1.20, 24),
        ("Butter Croissant", "Pastry", 2.80, 0.60, 12),
        ("Kuih Lapis", "Local", 1.50, 0.40, 48),
        ("Chicken Pie", "Savoury", 3.20, 0.90, 24),
        ("Baguette", "Bread", 3.00, 0.70, 12),
    ]
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO products (name, category, price, cost_to_make, shelf_life_hours) VALUES (?, ?, ?, ?, ?)",
            sample_products
        )
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")