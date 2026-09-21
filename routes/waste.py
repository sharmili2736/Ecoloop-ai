"""Waste Analyzer: image upload, demo classification and waste records."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import (
    api_login_required, award_points, current_user, login_required, one_of,
    positive_number, save_upload,
)
from services.ai_service import MODEL_AVAILABLE, classify_waste, estimate_impact
from services.analytics_service import WASTE_CATEGORIES, totals, waste_by_category

waste_bp = Blueprint("waste", __name__)

UNITS = ["kg", "g", "items"]


def _to_kg(quantity, unit):
    """Normalise a quantity to kilograms for impact maths."""
    if unit == "g":
        return quantity / 1000.0
    if unit == "items":
        return quantity * 0.05  # assume ~50 g per item
    return quantity


@waste_bp.route("/waste")
@login_required
def waste_page():
    user = current_user()
    return render_template(
        "waste.html",
        user=user,
        active_page="waste",
        categories=WASTE_CATEGORIES,
        units=UNITS,
        model_available=MODEL_AVAILABLE,
    )


@waste_bp.get("/api/waste")
@api_login_required
def api_list_waste():
    user = current_user()
    rows = query_db(
        "SELECT * FROM waste_records WHERE user_id = ? ORDER BY created_at DESC LIMIT 200",
        (user["id"],))
    t = totals(user["id"])
    return jsonify({
        "success": True,
        "records": rows_to_list(rows),
        "summary": {
            "total_waste": t["total_waste"],
            "plastic_waste": t["plastic_waste"],
            "recycling_rate": t["recycling_rate"],
            "records": len(rows),
        },
        "categories": waste_by_category(user["id"], months=12),
    })


@waste_bp.post("/api/waste/analyze")
@api_login_required
def api_analyze_waste():
    """Classify an uploaded image (or a chosen category) without saving a record."""
    category = request.form.get("category") or (request.get_json(silent=True) or {}).get("category")
    quantity_raw = request.form.get("quantity") or (request.get_json(silent=True) or {}).get("quantity") or 1
    unit = request.form.get("unit", "kg")

    image_path, error = save_upload(request.files.get("image"))
    if error:
        return jsonify({"success": False, "error": error}), 400

    if not image_path and not category:
        return jsonify({"success": False,
                        "error": "Upload an image or pick a waste category."}), 400

    quantity, quantity_error = positive_number(quantity_raw, "quantity")
    if quantity_error:
        return jsonify({"success": False, "error": quantity_error}), 400

    disk_path = None
    if image_path:
        from flask import current_app
        import os
        disk_path = os.path.join(current_app.config["UPLOAD_FOLDER"],
                                 os.path.basename(image_path))

    result = classify_waste(image_path=disk_path or image_path, selected_category=category)
    impact = estimate_impact(result, _to_kg(quantity, unit))

    return jsonify({
        "success": True,
        "result": result,
        "impact": impact,
        "image_path": image_path,
        "quantity": quantity,
        "unit": unit,
    })


@waste_bp.post("/api/waste")
@api_login_required
def api_create_waste():
    """Save a waste record, optionally including the analysis result."""
    user = current_user()
    data = request.form if request.form else (request.get_json(silent=True) or {})

    category, error = one_of(data.get("category"), WASTE_CATEGORIES, "waste category")
    if error:
        return jsonify({"success": False, "error": error}), 400

    quantity, error = positive_number(data.get("quantity"), "quantity")
    if error:
        return jsonify({"success": False, "error": error}), 400

    unit, error = one_of(data.get("unit", "kg"), UNITS, "unit")
    if error:
        return jsonify({"success": False, "error": error}), 400

    image_path = (data.get("image_path") or "").strip() or None
    if request.files.get("image"):
        image_path, upload_error = save_upload(request.files["image"])
        if upload_error:
            return jsonify({"success": False, "error": upload_error}), 400

    material = (data.get("material") or "").strip()[:120] or category
    try:
        confidence = float(data.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    record_id = execute_db(
        "INSERT INTO waste_records (user_id, category, material, quantity, unit, "
        "image_path, ai_result, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], category, material, quantity, unit, image_path,
         data.get("ai_result") or material, confidence,
         datetime.now().isoformat(timespec="seconds")),
    )

    points, total_points = award_points(user["id"], "waste_record")
    return jsonify({
        "success": True,
        "message": f"Waste record saved. +{points} eco points.",
        "id": record_id,
        "points_awarded": points,
        "eco_points": total_points,
    }), 201


@waste_bp.delete("/api/waste/<int:record_id>")
@api_login_required
def api_delete_waste(record_id):
    user = current_user()
    row = query_db("SELECT id FROM waste_records WHERE id = ? AND user_id = ?",
                   (record_id, user["id"]), one=True)
    if not row:
        return jsonify({"success": False, "error": "Record not found."}), 404
    execute_db("DELETE FROM waste_records WHERE id = ?", (record_id,))
    return jsonify({"success": True, "message": "Waste record deleted."})
