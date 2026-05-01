"""
Manual event tracking for bakery forecasting.
Allows managers to log local events that affect foot traffic.
"""
import sqlite3
from datetime import datetime

def add_event(store, date, event_type, description, impact="medium"):
    """Log a local event."""
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    conn.execute("""
        INSERT INTO events (store, date, event_type, description, expected_impact, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (store, date, event_type, description, impact, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()


def get_events_for_date(date):
    """Get all events for a specific date."""
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    events = conn.execute(
        "SELECT * FROM events WHERE date = ? ORDER BY created_at DESC",
        (date,)
    ).fetchall()
    
    conn.close()
    return events


def get_upcoming_events(days=7):
    """Get events for the next N days."""
    conn = sqlite3.connect("bakery.db")
    conn.row_factory = sqlite3.Row
    
    from datetime import timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    events = conn.execute(
        "SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY date",
        (today, end)
    ).fetchall()
    
    conn.close()
    return events


def delete_event(event_id):
    """Delete an event."""
    conn = sqlite3.connect("bakery.db")
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


def get_event_impact_score(date):
    """
    Calculate impact score for a date based on logged events.
    Returns 1.0 (normal), >1.0 (higher demand expected), <1.0 (lower demand).
    """
    events = get_events_for_date(date)
    
    if not events:
        return 1.0
    
    impact_map = {"low": 0.05, "medium": 0.15, "high": 0.30}
    boost_map = {
        "nearby_event": 1.0,
        "construction": 1.0,
        "school_activity": 1.2,
        "promotion": 1.3,
        "holiday_local": 1.5,
        "other": 1.0,
    }
    reduction_map = {
        "construction": -0.1,  # Construction might reduce walk-ins
        "other": 0,
    }
    
    total_impact = 1.0
    
    for event in events:
        impact = impact_map.get(event['expected_impact'], 0.15)
        boost = boost_map.get(event['event_type'], 1.0)
        reduction = reduction_map.get(event['event_type'], 0)
        
        total_impact += (impact * boost) + reduction
    
    return max(0.5, total_impact)  # Floor at 0.5, no ceiling


def apply_event_adjustments(forecast_results, target_date):
    """
    Adjust forecast recommendations based on logged events.
    If a high-impact event is logged, adjust quantities up or down.
    """
    impact_score = get_event_impact_score(target_date)
    events = get_events_for_date(target_date)
    
    for item in forecast_results:
        item['event_impact_score'] = impact_score
        
        if impact_score != 1.0:
            original = item['recommended']
            adjusted = round(original * impact_score)
            item['recommended'] = adjusted
            item['event_adjusted'] = True
            item['event_note'] = f"Adjusted by {((impact_score - 1) * 100):+.0f}% for logged events"
        else:
            item['event_adjusted'] = False
            item['event_note'] = ""
    
    return forecast_results, events