"""Carbon footprint calculator."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import api_login_required, award_points, current_user, login_required
from services.carbon_service import VEHICLES, calculate_footprint, factors_for_display

carbon_bp = Blueprint("carbon", __name__)


@carbon_bp.route("/carbon")
@login_required
def carbon_page():
    user = current_user()
    return render_template(
        "carbon.html",
        user=user,
        active_page="carbon",
        vehicles=VEHICLES,
        factors=factors_for_display(),
    )


@carbon_bp.get("/api/carbon")
@api_login_required
def api_carbon_history():
    user = current_user()
    rows = query_db(
        "SELECT * FROM carbon_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 24",
        (user["id"],))
    records = rows_to_list(rows)

    latest = records[0] if records else None
    previous = records[1] if len(records) > 1 else None
    change = None
    if latest and previous and previous["total_emissions"] > 0:
        change = round(
            (latest["total_emissions"] - previous["total_emissions"])
            / previous["total_emissions"] * 100, 1)

    return jsonify({
        "success": True,
        "records": records,
        "latest": latest,
        "previous": previous,
        "change_pct": change,
        "factors": factors_for_display(),
    })


@carbon_bp.post("/api/carbon/calculate")
@api_login_required
def api_calculate_carbon():
    user = current_user()
    data = request.get_json(silent=True) or request.form
    result = calculate_footprint(data)

    if result["monthly_total"] <= 0:
        return jsonify({"success": False,
                        "error": "Enter at least one value so there is something to estimate."}), 400

    save = str(data.get("save", "true")).lower() not in ("false", "0", "no")
    points, total_points = 0, user["eco_points"]

    if save:
        inputs, breakdown = result["inputs"], result["breakdown"]
        execute_db(
            "INSERT INTO carbon_records (user_id, electricity, transport_type, "
            "transport_distance, veg_meals, nonveg_meals, electricity_emissions, "
            "transport_emissions, food_emissions, waste_emissions, total_emissions, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], inputs["electricity"], inputs["transport_type"],
             inputs["transport_distance"], inputs["veg_meals"], inputs["nonveg_meals"],
             breakdown["electricity"], breakdown["transport"], breakdown["food"],
             breakdown["waste"], result["monthly_total"],
             datetime.now().isoformat(timespec="seconds")),
        )
        points, total_points = award_points(user["id"], "carbon_assessment")

    previous = query_db(
        "SELECT total_emissions FROM carbon_records WHERE user_id = ? "
        "ORDER BY created_at DESC LIMIT 1 OFFSET 1", (user["id"],), one=True)
    if previous and previous["total_emissions"] > 0:
        result["change_pct"] = round(
            (result["monthly_total"] - previous["total_emissions"])
            / previous["total_emissions"] * 100, 1)
        result["previous_total"] = round(previous["total_emissions"], 2)
    else:
        result["change_pct"] = None
        result["previous_total"] = None

    return jsonify({
        "success": True,
        "message": f"Footprint estimated. +{points} eco points." if points
                   else "Footprint estimated.",
        "result": result,
        "points_awarded": points,
        "eco_points": total_points,
    })
