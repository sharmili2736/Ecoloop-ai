"""
Aggregation layer.

The dashboard, the reports page and the recommendation engine all need the same
numbers, so they are computed in exactly one place here and read from SQLite.
"""

from datetime import datetime, timedelta

from config import BADGES, RECYCLING_SAVINGS
from models.database import query_db

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

WASTE_CATEGORIES = ["Plastic", "Paper", "Glass", "Metal",
                    "Organic", "E-Waste", "Textile", "Other"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _month_keys(count=6, end=None):
    """Return the last `count` months as (label, 'YYYY-MM') pairs, oldest first."""
    end = end or datetime.now()
    keys = []
    year, month = end.year, end.month
    for _ in range(count):
        keys.append((MONTH_LABELS[month - 1], f"{year:04d}-{month:02d}"))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


def _pct_change(current, previous):
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


def month_bounds(year, month):
    start = datetime(year, month, 1)
    end = datetime(year + (month == 12), (month % 12) + 1, 1)
    return start.isoformat(), end.isoformat()


# --------------------------------------------------------------------------- #
# Core aggregates
# --------------------------------------------------------------------------- #
def totals(user_id, start=None, end=None):
    """Headline totals for a user, optionally limited to a date window."""
    where, args = "user_id = ?", [user_id]
    if start and end:
        where += " AND created_at >= ? AND created_at < ?"
        args += [start, end]

    waste = query_db(
        f"SELECT COALESCE(SUM(quantity), 0) AS total FROM waste_records WHERE {where}",
        args, one=True)["total"]

    plastic_waste = query_db(
        f"SELECT COALESCE(SUM(quantity), 0) AS total FROM waste_records "
        f"WHERE {where} AND LOWER(category) = 'plastic'", args, one=True)["total"]

    recycled_rows = query_db(
        f"SELECT LOWER(material) AS material, COALESCE(SUM(quantity), 0) AS total "
        f"FROM recycling_records WHERE {where} GROUP BY LOWER(material)", args)

    recycled_by_material = {r["material"]: round(r["total"], 2) for r in recycled_rows}
    total_recycled = round(sum(recycled_by_material.values()), 2)
    plastic_recycled = recycled_by_material.get("plastic", 0)

    co2_saved = round(
        sum(qty * RECYCLING_SAVINGS.get(mat, 0.5)
            for mat, qty in recycled_by_material.items()), 2)

    carbon = query_db(
        f"SELECT COALESCE(AVG(total_emissions), 0) AS avg_total FROM carbon_records "
        f"WHERE {where}", args, one=True)["avg_total"]

    observations = query_db(
        f"SELECT COUNT(*) AS c FROM biodiversity_records WHERE {where}",
        args, one=True)["c"]

    return {
        "total_waste": round(waste, 2),
        "plastic_waste": round(plastic_waste, 2),
        "total_recycled": total_recycled,
        "plastic_recycled": plastic_recycled,
        "recycled_by_material": recycled_by_material,
        "co2_saved": co2_saved,
        "avg_monthly_carbon": round(carbon, 2),
        "observations": observations,
        "recycling_rate": round(min(total_recycled / waste * 100, 100), 1) if waste > 0 else 0.0,
    }


def waste_by_category(user_id, months=6):
    """Totals per waste category over the recent window, for the doughnut chart."""
    since = (datetime.now() - timedelta(days=30 * months)).isoformat()
    rows = query_db(
        "SELECT category, COALESCE(SUM(quantity), 0) AS total FROM waste_records "
        "WHERE user_id = ? AND created_at >= ? GROUP BY category ORDER BY total DESC",
        (user_id, since))
    return [{"category": r["category"], "total": round(r["total"], 2)} for r in rows]


def monthly_series(user_id, months=6):
    """Waste generated, recycled and carbon for each of the last `months` months."""
    keys = _month_keys(months)
    labels = [label for label, _ in keys]

    def series(table, column, aggregate="SUM"):
        out = []
        for _, key in keys:
            row = query_db(
                f"SELECT COALESCE({aggregate}({column}), 0) AS v FROM {table} "
                f"WHERE user_id = ? AND strftime('%Y-%m', created_at) = ?",
                (user_id, key), one=True)
            out.append(round(row["v"], 2))
        return out

    generated = series("waste_records", "quantity")
    recycled = series("recycling_records", "quantity")
    carbon = series("carbon_records", "total_emissions", "AVG")
    rate = [round(min(r / g * 100, 100), 1) if g > 0 else 0 for g, r in zip(generated, recycled)]

    return {
        "labels": labels,
        "waste_generated": generated,
        "recycled": recycled,
        "recycling_rate": rate,
        "carbon": carbon,
    }


def sustainability_score(user_id):
    """
    Composite 0-100 score built from five equally weighted pillars.
    Each pillar is itself scored 0-100 so the breakdown is explainable.
    """
    t = totals(user_id)
    series = monthly_series(user_id, months=2)

    # 1. Waste management: rewards keeping monthly waste low (25 kg = floor).
    this_month = series["waste_generated"][-1]
    waste_score = 100 if this_month == 0 else max(0, min(100, (1 - this_month / 25) * 100 + 40))

    # 2. Recycling: the share of generated waste that was recycled.
    recycling_score = min(t["recycling_rate"] * 1.25, 100)

    # 3. Carbon: 150 kg CO2e/month scores 0, 0 kg scores 100.
    carbon = t["avg_monthly_carbon"]
    carbon_score = 60 if carbon == 0 else max(0, min(100, (1 - carbon / 300) * 100))

    # 4. Eco actions: challenges completed and goals met.
    completed = query_db(
        "SELECT COUNT(*) AS c FROM user_challenges WHERE user_id = ? AND status = 'Completed'",
        (user_id,), one=True)["c"]
    goals_done = query_db(
        "SELECT COUNT(*) AS c FROM zero_waste_goals WHERE user_id = ? AND status = 'Completed'",
        (user_id,), one=True)["c"]
    actions_score = min((completed * 20) + (goals_done * 15), 100)

    # 5. Biodiversity: 15 observations is full marks.
    bio_score = min(t["observations"] / 15 * 100, 100)

    pillars = {
        "Waste Management": round(waste_score),
        "Recycling": round(recycling_score),
        "Carbon Reduction": round(carbon_score),
        "Eco Actions": round(actions_score),
        "Biodiversity": round(bio_score),
    }
    overall = round(sum(pillars.values()) / len(pillars))
    return {"score": overall, "pillars": pillars}


def trend_snapshot(user_id):
    """Month-over-month changes used by the insight engine and stat cards."""
    series = monthly_series(user_id, months=2)
    waste_now, waste_prev = series["waste_generated"][-1], series["waste_generated"][0]
    recycled_now, recycled_prev = series["recycled"][-1], series["recycled"][0]
    carbon_now, carbon_prev = series["carbon"][-1], series["carbon"][0]

    categories = waste_by_category(user_id, months=1)
    return {
        "waste_change_pct": _pct_change(waste_now, waste_prev),
        "recyclable_change_pct": _pct_change(recycled_now, recycled_prev),
        "carbon_change_pct": _pct_change(carbon_now, carbon_prev),
        "carbon_this_month": carbon_now,
        "carbon_last_month": carbon_prev,
        "top_waste_category": categories[0]["category"] if categories else None,
    }


def earned_badges(user_id, eco_points):
    """Evaluate every badge against the user's activity."""
    t = totals(user_id)
    actions = query_db(
        "SELECT (SELECT COUNT(*) FROM waste_records WHERE user_id = ?) + "
        "(SELECT COUNT(*) FROM recycling_records WHERE user_id = ?) + "
        "(SELECT COUNT(*) FROM biodiversity_records WHERE user_id = ?) AS c",
        (user_id, user_id, user_id), one=True)["c"]

    metrics = {
        "actions": actions,
        "plastic_recycled": t["plastic_recycled"],
        "total_recycled": t["total_recycled"],
        "co2_saved": t["co2_saved"],
        "observations": t["observations"],
        "eco_points": eco_points,
    }

    badges = []
    for badge in BADGES:
        value = metrics.get(badge["metric"], 0)
        badges.append({
            **badge,
            "earned": value >= badge["threshold"],
            "progress": round(min(value / badge["threshold"] * 100, 100)),
            "value": round(value, 1),
        })
    return badges


def dashboard_payload(user):
    """Everything the dashboard page needs, in one object."""
    user_id = user["id"]
    t = totals(user_id)
    trends = trend_snapshot(user_id)
    score = sustainability_score(user_id)

    goals = query_db(
        "SELECT id, title, target, current, unit, deadline, status FROM zero_waste_goals "
        "WHERE user_id = ? ORDER BY (status = 'Completed'), deadline LIMIT 4", (user_id,))

    challenges = query_db(
        "SELECT c.id, c.title, c.points, c.icon, uc.progress, uc.status "
        "FROM user_challenges uc JOIN challenges c ON c.id = uc.challenge_id "
        "WHERE uc.user_id = ? ORDER BY (uc.status = 'Completed'), uc.joined_at DESC LIMIT 4",
        (user_id,))

    bio = query_db(
        "SELECT category, COUNT(*) AS c FROM biodiversity_records WHERE user_id = ? "
        "GROUP BY category ORDER BY c DESC", (user_id,))

    this_month_obs = query_db(
        "SELECT COUNT(*) AS c FROM biodiversity_records WHERE user_id = ? "
        "AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
        (user_id,), one=True)["c"]

    return {
        "user": {
            "name": user["name"],
            "eco_points": user["eco_points"],
            "user_type": user["user_type"],
            "organization": user["organization"],
        },
        "totals": t,
        "trends": trends,
        "score": score,
        "charts": monthly_series(user_id, months=6),
        "waste_categories": waste_by_category(user_id, months=6),
        "goals": [dict(g) for g in goals],
        "challenges": [dict(c) for c in challenges],
        "biodiversity": {
            "by_category": [dict(b) for b in bio],
            "this_month": this_month_obs,
            "total": t["observations"],
        },
        "badges": earned_badges(user_id, user["eco_points"]),
    }
