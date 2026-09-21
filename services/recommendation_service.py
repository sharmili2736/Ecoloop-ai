"""
Recommendation engine.

Rule-based and fully explainable: every suggestion is triggered by a stored
number, and the number is quoted back to the user. `generate_recommendations()`
returns plain dicts, so swapping in an LLM later only means changing this file.
"""

from datetime import datetime

from models.database import execute_db, query_db
from services.analytics_service import totals, trend_snapshot, monthly_series

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _rule_set(user_id):
    """Evaluate every rule against the user's data and return matching advice."""
    t = totals(user_id)
    trends = trend_snapshot(user_id)
    series = monthly_series(user_id, months=2)
    out = []

    latest_carbon = query_db(
        "SELECT * FROM carbon_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,), one=True)

    # --- Electricity ---------------------------------------------------------
    if latest_carbon and latest_carbon["electricity"] > 150:
        units = latest_carbon["electricity"]
        saving = round(units * 0.10 * 0.82, 1)
        out.append({
            "title": "Bring down your electricity use",
            "description": (f"Your last assessment recorded {units:.0f} kWh in a month, "
                            f"which is the largest single driver of your estimated footprint."),
            "action": "Switch to LED lighting, raise the AC setpoint by 2 °C, and unplug idle chargers.",
            "impact": f"A 10% cut saves roughly {saving} kg CO₂e per month.",
            "difficulty": "Easy",
            "priority": "High",
            "icon": "bolt",
        })

    # --- Transport -----------------------------------------------------------
    if latest_carbon and latest_carbon["transport_type"] in ("petrol_car", "diesel_car") \
            and latest_carbon["transport_distance"] > 200:
        km = latest_carbon["transport_distance"]
        saving = round(km * 0.25 * (0.192 - 0.089), 1)
        out.append({
            "title": "Shift a quarter of your car trips to the bus",
            "description": (f"You logged {km:.0f} km by car last month. Short repeat trips "
                            f"are usually the easiest ones to replace."),
            "action": "Pick the three journeys you make most often and take the bus or train instead.",
            "impact": f"Around {saving} kg CO₂e per month.",
            "difficulty": "Medium",
            "priority": "High",
            "icon": "bus",
        })

    # --- Plastic -------------------------------------------------------------
    plastic_share = (t["plastic_waste"] / t["total_waste"] * 100) if t["total_waste"] else 0
    if plastic_share > 20:
        out.append({
            "title": "Cut single-use plastic",
            "description": (f"Plastic is {plastic_share:.0f}% of the waste you have logged, "
                            f"which is high enough to be worth targeting first."),
            "action": "Carry a refillable bottle and a cloth bag; refuse plastic cutlery and straws.",
            "impact": "Avoiding 1 kg of plastic keeps about 2.75 kg CO₂e out of the atmosphere.",
            "difficulty": "Easy",
            "priority": "High",
            "icon": "bottle-water",
        })

    # --- Recycling rate ------------------------------------------------------
    if t["total_waste"] > 0 and t["recycling_rate"] < 40:
        out.append({
            "title": "Separate recyclables at source",
            "description": (f"Only {t['recycling_rate']:.0f}% of your logged waste has been "
                            f"recycled. Mixed bins are the usual reason material gets rejected."),
            "action": "Keep three labelled bins: dry recyclables, wet organic waste, and rejects.",
            "impact": "Lifting your rate to 60% would roughly double your avoided emissions.",
            "difficulty": "Easy",
            "priority": "High",
            "icon": "recycle",
        })

    # --- Organic waste -------------------------------------------------------
    organic = query_db(
        "SELECT COALESCE(SUM(quantity), 0) AS q FROM waste_records "
        "WHERE user_id = ? AND LOWER(category) = 'organic'", (user_id,), one=True)["q"]
    if organic > 5:
        out.append({
            "title": "Start composting your food waste",
            "description": f"You have logged {organic:.1f} kg of organic waste. In landfill it "
                           f"breaks down anaerobically and releases methane.",
            "action": "Set up a small compost bin or join a community composting point.",
            "impact": f"Composting this volume avoids about {round(organic * 0.4, 1)} kg CO₂e.",
            "difficulty": "Medium",
            "priority": "Medium",
            "icon": "seedling",
        })

    # --- Waste trending up ---------------------------------------------------
    if trends["waste_change_pct"] > 15:
        out.append({
            "title": "Your waste volume is climbing",
            "description": f"You generated {trends['waste_change_pct']:.0f}% more waste this "
                           f"month than last month.",
            "action": "Audit one week of purchases and identify the three biggest packaging sources.",
            "impact": "Returning to last month's level would cut roughly "
                      f"{round(abs(series['waste_generated'][-1] - series['waste_generated'][0]), 1)} kg of waste.",
            "difficulty": "Medium",
            "priority": "Medium",
            "icon": "chart-line",
        })

    # --- Biodiversity --------------------------------------------------------
    if t["observations"] < 5:
        out.append({
            "title": "Record what lives around you",
            "description": "You have fewer than five species observations logged, so there is "
                           "not yet enough data to show change over time.",
            "action": "Spend fifteen minutes a week noting birds, trees and insects near you.",
            "impact": "Builds a local baseline and earns 15 eco points per observation.",
            "difficulty": "Easy",
            "priority": "Low",
            "icon": "dove",
        })

    # --- Fallback ------------------------------------------------------------
    if not out:
        out.append({
            "title": "Keep your streak going",
            "description": "Your recycling rate, footprint and waste volume are all in good shape.",
            "action": "Take on a new eco challenge to hold the habit in place.",
            "impact": "Completed challenges add 35-70 eco points each.",
            "difficulty": "Easy",
            "priority": "Low",
            "icon": "trophy",
        })

    out.sort(key=lambda r: PRIORITY_ORDER[r["priority"]])
    return out


def generate_recommendations(user_id, persist=True):
    """
    Build the current recommendation set. When `persist` is true the stored set
    is replaced so the recommendations table always mirrors the latest data.
    """
    recs = _rule_set(user_id)
    if persist:
        execute_db("DELETE FROM recommendations WHERE user_id = ?", (user_id,))
        now = datetime.now().isoformat(timespec="seconds")
        for r in recs:
            execute_db(
                "INSERT INTO recommendations (user_id, title, description, action, "
                "priority, impact, difficulty, icon, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, r["title"], r["description"], r["action"], r["priority"],
                 r["impact"], r["difficulty"], r["icon"], now),
            )
    return recs
