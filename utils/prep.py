import sqlite3
from datetime import datetime
from db import get_db

def get_todays_prep_list():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")

    # Get today's plan
    plan = conn.execute("SELECT id FROM production_plans WHERE date = ?", (today,)).fetchone()
    if not plan:
        conn.close()
        return []

    # Get scheduled items
    items = conn.execute("""
        SELECT pi.id as item_id, pi.product_id, p.name as product_name, 
               COALESCE(pi.baker_override, pi.ai_recommended, 0) as target_qty
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
    """, (plan["id"],)).fetchall()

    prep_list = []
    for item in items:
        target_qty = item["target_qty"]
        
        # Get ingredients
        ingredients = conn.execute("""
            SELECT i.name, i.unit, r.coefficient_grams,
                   (r.coefficient_grams * ?) as needed_grams
            FROM recipes r
            JOIN ingredients i ON r.ingredient_id = i.id
            WHERE r.product_id = ?
        """, (target_qty, item["product_id"])).fetchall()

        prep_list.append({
            "item_id": item["item_id"],
            "product_id": item["product_id"],
            "product_name": item["product_name"],
            "target_qty": target_qty,
            "ingredients": [dict(i) for i in ingredients]
        })

    conn.close()
    return prep_list

def start_batch(item_id, product_id, target_qty):
    """Deducts ingredients & creates production run"""
    print(f"🔧 STARTING BATCH: item_id={item_id}, product_id={product_id}, qty={target_qty}")
    
    conn = get_db()
    conn.row_factory = sqlite3.Row  # Ensure row factory is set
    
    # 1. Create run
    print("  1. Creating production run...")
    run = conn.execute("""
        INSERT INTO production_runs (product_id, quantity_baked, status)
        VALUES (?, ?, 'in_progress')
    """, (product_id, target_qty))
    run_id = run.lastrowid  # Use lastrowid instead of RETURNING
    print(f"     → Run ID: {run_id}")

    # 2. Check recipes
    print("  2. Fetching recipes...")
    recipes = conn.execute("""
        SELECT ingredient_id, coefficient_grams 
        FROM recipes 
        WHERE product_id = ?
    """, (product_id,)).fetchall()
    
    print(f"     → Found {len(recipes)} recipe(s)")
    for r in recipes:
        print(f"        - Ingredient {r['ingredient_id']}: {r['coefficient_grams']}g")

    # 3. Deduct ingredients
    for r in recipes:
        qty = r["coefficient_grams"] * target_qty
        print(f"  3. Deducting {qty}g from ingredient {r['ingredient_id']}")
        
        conn.execute("""
            INSERT INTO inventory_transactions (ingredient_id, type, quantity, reference_id)
            VALUES (?, 'production', ?, ?)
        """, (r["ingredient_id"], -qty, run_id))
        
        conn.execute("""
            UPDATE ingredients 
            SET current_stock = current_stock - ? 
            WHERE id = ?
        """, (qty, r["ingredient_id"]))

    # 4. Update plan_items
    print(f"  4. Updating plan_items {item_id} with produced={target_qty}")
    conn.execute("""
        UPDATE plan_items 
        SET actually_produced = ? 
        WHERE id = ?
    """, (target_qty, item_id))
    
    # 5. Commit
    print("  5. Committing transaction...")
    conn.commit()
    conn.close()
    
    print(f"✅ BATCH STARTED SUCCESSFULLY (Run ID: {run_id})")
    return run_id

def complete_batch(run_id):
    conn = get_db()
    conn.execute("UPDATE production_runs SET status = 'completed', completed_at = datetime('now') WHERE id = ?", (run_id,))
    conn.commit()
    conn.close()