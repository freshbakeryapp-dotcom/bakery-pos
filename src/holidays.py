"""
Holiday proximity features for Brunei bakeries.
Calculates "days until" major holidays.
"""
from datetime import datetime, timedelta

BRUNEI_HOLIDAYS = [
    ("New Year's Day", "2026-01-01"),
    ("Chinese New Year", "2026-02-17"),
    ("National Day", "2026-02-23"),
    ("Israk Mikraj", "2026-03-16"),
    ("First Day of Ramadan", "2026-03-20"),
    ("Hari Raya Aidilfitri", "2026-04-20"),
    ("Royal Brunei Armed Forces Day", "2026-05-31"),
    ("Hari Raya Aidiladha", "2026-06-27"),
    ("His Majesty's Birthday", "2026-07-15"),
    ("Islamic New Year", "2026-08-09"),
    ("Prophet's Birthday", "2026-10-18"),
    ("Christmas Day", "2026-12-25"),
]

def get_upcoming_holiday(date_str, days_ahead=14):
    """Get the next upcoming holiday within N days."""
    target = datetime.strptime(date_str, "%Y-%m-%d")
    
    upcoming = []
    for name, hol_date in BRUNEI_HOLIDAYS:
        hol_dt = datetime.strptime(hol_date, "%Y-%m-%d")
        days_until = (hol_dt - target).days
        
        if 0 <= days_until <= days_ahead:
            upcoming.append({
                "name": name,
                "date": hol_date,
                "days_until": days_until,
            })
    
    return sorted(upcoming, key=lambda x: x['days_until'])


def get_holiday_proximity_features(date_str):
    """Calculate holiday proximity features for a date."""
    target = datetime.strptime(date_str, "%Y-%m-%d")
    
    features = {
        "days_until_next_holiday": 30,
        "is_holiday_today": False,
        "is_pre_holiday_week": False,
        "is_ramadan": False,
        "upcoming_holiday_name": "",
    }
    
    for name, hol_date in BRUNEI_HOLIDAYS:
        hol_dt = datetime.strptime(hol_date, "%Y-%m-%d")
        days_until = (hol_dt - target).days
        
        if days_until == 0:
            features["is_holiday_today"] = True
            features["days_until_next_holiday"] = 0
            features["upcoming_holiday_name"] = name
        
        if 0 < days_until < features["days_until_next_holiday"]:
            features["days_until_next_holiday"] = days_until
            features["upcoming_holiday_name"] = name
        
        if 0 < days_until <= 3:
            features["is_pre_holiday_week"] = True
        
        if "Ramadan" in name and days_until > 0:
            features["is_ramadan"] = True
    
    for name, hol_date in BRUNEI_HOLIDAYS:
        if "Hari Raya" in name:
            hol_dt = datetime.strptime(hol_date, "%Y-%m-%d")
            days_until = (hol_dt - target).days
            if 0 < days_until <= 7:
                features["is_pre_holiday_week"] = True
    
    return features


def apply_holiday_multiplier(recommended, date_str):
    """Adjust forecast for holiday effects."""
    features = get_holiday_proximity_features(date_str)
    
    multiplier = 1.0
    note = ""
    
    if features["is_holiday_today"]:
        multiplier = 0.70
        note = f"Holiday ({features['upcoming_holiday_name']}) — reduced demand"
    elif features["is_pre_holiday_week"]:
        multiplier = 1.20
        note = f"Pre-holiday week ({features['upcoming_holiday_name']} in {features['days_until_next_holiday']} days) — increased demand"
    elif features["is_ramadan"]:
        multiplier = 1.15
        note = "Ramadan period — increased demand"
    
    adjusted = round(recommended * multiplier)
    
    return adjusted, note, features