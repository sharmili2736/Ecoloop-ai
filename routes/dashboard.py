"""Dashboard page, aggregate API and the recommendations endpoint."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template

from routes import api_login_required, current_user, login_required
from services.ai_service import generate_sustainability_insight
from services.analytics_service import dashboard_payload
from services.recommendation_service import generate_recommendations

dashboard_bp = Blueprint("dashboard", __name__)


def _greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    return "Good evening"


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_page():
    user = current_user()
    return render_template(
        "dashboard.html",
        user=user,
        active_page="dashboard",
        greeting=_greeting(),
    )


@dashboard_bp.get("/api/dashboard")
@api_login_required
def api_dashboard():
    user = current_user()
    payload = dashboard_payload(user)

    insight_input = {
        "recycling_rate": payload["totals"]["recycling_rate"],
        "recyclable_change_pct": payload["trends"]["recyclable_change_pct"],
        "carbon_change_pct": payload["trends"]["carbon_change_pct"],
        "top_waste_category": payload["trends"]["top_waste_category"],
        "total_waste": payload["totals"]["total_waste"],
    }
    payload["insight"] = generate_sustainability_insight(insight_input)
    payload["greeting"] = _greeting()
    payload["recommendations"] = generate_recommendations(user["id"])[:3]
    return jsonify({"success": True, "data": payload})


@dashboard_bp.get("/api/recommendations")
@api_login_required
def api_recommendations():
    user = current_user()
    return jsonify({
        "success": True,
        "recommendations": generate_recommendations(user["id"]),
    })
