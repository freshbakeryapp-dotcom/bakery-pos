def save_forecast_to_db(forecast_results, target_date=None):
    """Save a generated forecast to the production_plans table."""
    if target_date is None:
        target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    # Create plan
    cursor = conn.execute(
        "INSERT INTO production_plans (store, date, created_at) VALUES (?, ?, ?)",
        ("All", target_date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    plan_id = cursor.lastrowid
    
    # Get product ID lookup
    product_map = {}
    for row in conn.execute("SELECT id, name FROM products"):
        product_map[row['name'].lower()] = row['id']
    
    # Insert plan items
    for item in forecast_results:
        product_id = product_map.get(item['product'].lower())
        if product_id:
            conn.execute(
                "INSERT INTO plan_items (plan_id, product_id, ai_recommended) VALUES (?, ?, ?)",
                (plan_id, product_id, item['recommended'])
            )
    
    conn.commit()
    conn.close()
    return plan_id