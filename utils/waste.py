import sqlite3
from datetime import datetime
from db import get_db

def get_wrap_up_data():
    """Fetches today's production vs sales for wrap-up logging."""
    conn = get_db()
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    
    plan = conn.execute("SELECT id FROM production_plans WHERE date = ?", (today,)).fetchone()
    if not plan:
        conn.close()
        return []
        
    # Get plan items with production & sales data
    items = conn.execute("""
        SELECT pi.id as item_id, pi.product_id, p.name as product_name,
               COALESCE(pi.actually_produced, 0) as produced,
               COALESCE(pi.actually_sold, 0) as sold,
               COALESCE(pi.wasted, 0) as wasted,
               pi.waste_reason
        FROM plan_items pi
        JOIN products p ON pi.product_id = p.id
        WHERE pi.plan_id = ?
    """, (plan["id"],)).fetchall()
    
    results = []
    for item in items:
        remaining = item["produced"] - item["sold"] - item["wasted"]
        results.append({
            "item_id": item["item_id"],
            "product_name": item["product_name"],
            "produced": item["produced"],
            "sold": item["sold"],
            "remaining": remaining,
            "wasted": item["wasted"],
            "reason": item["waste_reason"]
        })
        
    conn.close()
    return results

def log_waste(item_id, quantity, reason):
    """Logs waste and updates AI training signals."""
    conn = get_db()
    
    # 1. Update plan_items with waste count and reason
    conn.execute("""
        UPDATE plan_items 
        SET wasted = COALESCE(wasted, 0) + ?, waste_reason = ?
        WHERE id = ?
    """, (quantity, reason, item_id))
    
    # 2. Update production_runs status to 'completed'
    run = conn.execute("SELECT product_id FROM plan_items WHERE id = ?", (item_id,)).fetchone()
    if run:
        conn.execute("""
            UPDATE production_runs 
            SET status = 'completed', completed_at = datetime('now')
            WHERE product_id = ? AND status = 'in_progress'
        """, (run[0],))
        
    conn.commit()
    conn.close()
    return True

def get_ai_waste_insights():
    """Returns simple insights for the baker."""
    conn = get_db()
    month = datetime.now().strftime("%Y-%m")
    
    # Calculate waste rate by reason
    insights = conn.execute("""
        SELECT waste_reason, SUM(wasted) as total_wasted, COUNT(*) as occurrences
        FROM plan_items 
        WHERE waste_reason IS NOT NULL AND waste_reason != ''
        GROUP BY waste_reason
        ORDER BY total_wasted DESC
    """).fetchall()
    
    conn.close()
    return insights