CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ingredient_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    quantity REAL NOT NULL,
    reference_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS production_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    quantity_baked REAL NOT NULL,
    status TEXT DEFAULT 'planned',
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    coefficient_grams REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS monthly_usage_coeffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    coefficient REAL NOT NULL,
    confidence REAL NOT NULL,
    data_points INTEGER NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(product_id, ingredient_id, month)
);