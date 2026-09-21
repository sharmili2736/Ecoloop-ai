"""Recycling tracker."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import (
    api_login_required, award_points, current_user, login_required, one_of,
    positive_number,
)
from services.analytics_service import monthly_series, totals
from services.carbon_service import recycling_co2_saved

recycling_bp = Blueprint("recycling", __name__)

MATERIALS = ["Plastic", "Paper", "Glass", "Metal", "Organic", "E-Waste", "Textile", "Other"]
UNITS = ["kg", "g", "items"]
METHODS = ["Municipal collection", "Campus recycling drive", "Scrap dealer",
           "Compost pit", "Take-back programme", "Other"]

# Default goals shown as progress bars on the recycling page.
MATERIAL_GOALS = {"Plastic": 100, "Paper": 100, "Glass": 50, "Metal": 50, "Organic": 60}


@recycling_bp.route("/recycling")
@login_required
def recycling_page():
    user = current_user()
    return render_template(
        "recycling.html",
        user=user,
        active_page="recycling",
        materials=MATERIALS,
        units=UNITS,
        methods=METHODS,
    )


@recycling_bp.get("/api/recycling")
@api_login_required
def api_list_recycling():
    user = current_user()
    rows = query_db(
        "SELECT * FROM recycling_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
        (user["id"],))
    t = totals(user["id"])
    by_material = t["recycled_by_material"]

    goals = [
        {
            "material": material,
            "target": target,
            "current": round(by_material.get(material.lower(), 0), 2),
            "percent": round(min(by_material.get(material.lower(), 0) / target * 100, 100), 1),
        }
        for material, target in MATERIAL_GOALS.items()
    ]

    return jsonify({
        "success": True,
        "records": rows_to_list(rows),
        "summary": {
            "total_recycled": t["total_recycled"],
            "by_material": by_material,
            "co2_saved": t["co2_saved"],
            "records": len(rows),
        },
        "goals": goals,
        "trend": monthly_series(user["id"], months=6),
    })


@recycling_bp.post("/api/recycling")
@api_login_required
def api_create_recycling():
    user = current_user()
    data = request.get_json(silent=True) or request.form

    material, error = one_of(data.get("material"), MATERIALS, "material")
    if error:
        return jsonify({"success": False, "error": error}), 400

    quantity, error = positive_number(data.get("quantity"), "quantity")
    if error:
        return jsonify({"success": False, "error": error}), 400

    unit, error = one_of(data.get("unit", "kg"), UNITS, "unit")
    if error:
        return jsonify({"success": False, "error": error}), 400

    method = (data.get("method") or "Municipal collection").strip()[:120]
    notes = (data.get("notes") or "").strip()[:500]

    created_at = (data.get("date") or "").strip()
    try:
        created_at = (datetime.fromisoformat(created_at) if created_at
                      else datetime.now()).isoformat(timespec="seconds")
    except ValueError:
        return jsonify({"success": False, "error": "Enter a valid date."}), 400

    record_id = execute_db(
        "INSERT INTO recycling_records (user_id, material, quantity, unit, method, "
        "notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user["id"], material, quantity, unit, method, notes, created_at),
    )

    points, total_points = award_points(user["id"], "recycling_record")
    return jsonify({
        "success": True,
        "message": f"Recycling logged. +{points} eco points.",
        "id": record_id,
        "co2_saved": recycling_co2_saved(material, quantity if unit == "kg" else quantity / 1000),
        "points_awarded": points,
        "eco_points": total_points,
    }), 201


@recycling_bp.delete("/api/recycling/<int:record_id>")
@api_login_required
def api_delete_recycling(record_id):
    user = current_user()
    row = query_db("SELECT id FROM recycling_records WHERE id = ? AND user_id = ?",
                   (record_id, user["id"]), one=True)
    if not row:
        return jsonify({"success": False, "error": "Record not found."}), 404
    execute_db("DELETE FROM recycling_records WHERE id = ?", (record_id,))
    return jsonify({"success": True, "message": "Recycling record deleted."})
