"""Biodiversity Monitor: species observations with a lightweight sketch map."""

import random
from datetime import date, datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import (
    api_login_required, award_points, current_user, login_required, one_of,
    required_text, save_upload,
)

biodiversity_bp = Blueprint("biodiversity", __name__)

CATEGORIES = ["Bird", "Plant", "Butterfly", "Insect", "Tree", "Small Animal"]


@biodiversity_bp.route("/biodiversity")
@login_required
def biodiversity_page():
    user = current_user()
    return render_template(
        "biodiversity.html", user=user, active_page="biodiversity", categories=CATEGORIES)


@biodiversity_bp.get("/api/biodiversity")
@api_login_required
def api_list_biodiversity():
    user = current_user()
    rows = query_db(
        "SELECT * FROM biodiversity_records WHERE user_id = ? ORDER BY "
        "observation_date DESC, created_at DESC LIMIT 200", (user["id"],))
    records = rows_to_list(rows)

    by_category = {}
    for r in records:
        by_category[r["category"]] = by_category.get(r["category"], 0) + 1

    this_month = query_db(
        "SELECT COUNT(*) AS c FROM biodiversity_records WHERE user_id = ? "
        "AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')",
        (user["id"],), one=True)["c"]

    unique_species = len({r["species"].strip().lower() for r in records})

    return jsonify({
        "success": True,
        "records": records,
        "summary": {
            "species_observed": unique_species,
            "observations": len(records),
            "plants": by_category.get("Plant", 0) + by_category.get("Tree", 0),
            "birds": by_category.get("Bird", 0),
            "this_month": this_month,
            "by_category": by_category,
        },
        "categories": CATEGORIES,
    })


@biodiversity_bp.post("/api/biodiversity")
@api_login_required
def api_create_biodiversity():
    user = current_user()
    data = request.form if request.form else (request.get_json(silent=True) or {})

    species, error = required_text(data.get("species"), "Species name", 120)
    if error:
        return jsonify({"success": False, "error": error}), 400

    category, error = one_of(data.get("category"), CATEGORIES, "category")
    if error:
        return jsonify({"success": False, "error": error}), 400

    location = (data.get("location") or "").strip()[:160]
    description = (data.get("description") or "").strip()[:600]

    observation_date = (data.get("observation_date") or "").strip() or date.today().isoformat()
    try:
        date.fromisoformat(observation_date)
    except ValueError:
        return jsonify({"success": False, "error": "Enter a valid observation date."}), 400

    image_path, upload_error = save_upload(request.files.get("image"))
    if upload_error:
        return jsonify({"success": False, "error": upload_error}), 400

    # Sketch-map coordinates: no GPS, no external map service. The record is
    # simply placed on a stylised campus grid so observations are visualised.
    record_id = execute_db(
        "INSERT INTO biodiversity_records (user_id, species, category, location, "
        "observation_date, description, image_path, map_x, map_y, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], species, category, location, observation_date, description,
         image_path, round(random.uniform(8, 92), 1), round(random.uniform(10, 88), 1),
         datetime.now().isoformat(timespec="seconds")),
    )

    points, total_points = award_points(user["id"], "biodiversity_record")
    return jsonify({
        "success": True,
        "message": f"Observation recorded. +{points} eco points.",
        "id": record_id,
        "points_awarded": points,
        "eco_points": total_points,
    }), 201


@biodiversity_bp.delete("/api/biodiversity/<int:record_id>")
@api_login_required
def api_delete_biodiversity(record_id):
    user = current_user()
    row = query_db("SELECT id FROM biodiversity_records WHERE id = ? AND user_id = ?",
                   (record_id, user["id"]), one=True)
    if not row:
        return jsonify({"success": False, "error": "Observation not found."}), 404
    execute_db("DELETE FROM biodiversity_records WHERE id = ?", (record_id,))
    return jsonify({"success": True, "message": "Observation deleted."})
