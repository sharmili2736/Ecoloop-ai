"""Zero-Waste Planner: goal CRUD and progress updates."""

from datetime import date, datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import (
    api_login_required, award_points, current_user, login_required,
    positive_number, required_text,
)

goals_bp = Blueprint("goals", __name__)

UNITS = ["kg", "items", "%", "trips", "bottles"]


def _refresh_status(goal):
    """Derive a goal's status from its progress and deadline."""
    if goal["current"] >= goal["target"]:
        return "Completed"
    if goal["deadline"]:
        try:
            if date.fromisoformat(goal["deadline"]) < date.today():
                return "Overdue"
        except ValueError:
            pass
    return "Active"


@goals_bp.route("/zero-waste")
@login_required
def zero_waste_page():
    user = current_user()
    return render_template(
        "zero_waste.html", user=user, active_page="zero-waste", units=UNITS)


@goals_bp.get("/api/goals")
@api_login_required
def api_list_goals():
    user = current_user()
    rows = query_db(
        "SELECT * FROM zero_waste_goals WHERE user_id = ? ORDER BY "
        "(status = 'Completed'), deadline IS NULL, deadline", (user["id"],))

    goals = []
    for row in rows_to_list(rows):
        status = _refresh_status(row)
        if status != row["status"]:
            execute_db("UPDATE zero_waste_goals SET status = ? WHERE id = ?",
                       (status, row["id"]))
            row["status"] = status
        row["percent"] = round(min(row["current"] / row["target"] * 100, 100), 1) \
            if row["target"] > 0 else 0
        goals.append(row)

    summary = {
        "total": len(goals),
        "active": sum(1 for g in goals if g["status"] == "Active"),
        "completed": sum(1 for g in goals if g["status"] == "Completed"),
        "overdue": sum(1 for g in goals if g["status"] == "Overdue"),
        "avg_progress": round(sum(g["percent"] for g in goals) / len(goals), 1) if goals else 0,
    }
    return jsonify({"success": True, "goals": goals, "summary": summary})


@goals_bp.post("/api/goals")
@api_login_required
def api_create_goal():
    user = current_user()
    data = request.get_json(silent=True) or request.form

    title, error = required_text(data.get("title"), "Goal name", 120)
    if error:
        return jsonify({"success": False, "error": error}), 400

    target, error = positive_number(data.get("target"), "target")
    if error:
        return jsonify({"success": False, "error": error}), 400

    try:
        current_value = max(float(data.get("current") or 0), 0)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Enter a valid current value."}), 400

    unit = (data.get("unit") or "kg").strip()
    if unit not in UNITS:
        unit = "kg"

    deadline = (data.get("deadline") or "").strip() or None
    if deadline:
        try:
            date.fromisoformat(deadline)
        except ValueError:
            return jsonify({"success": False, "error": "Enter a valid deadline date."}), 400

    goal_id = execute_db(
        "INSERT INTO zero_waste_goals (user_id, title, target, current, unit, deadline, "
        "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user["id"], title, target, current_value, unit, deadline, "Active",
         datetime.now().isoformat(timespec="seconds")),
    )
    return jsonify({"success": True, "message": "Goal created.", "id": goal_id}), 201


@goals_bp.put("/api/goals/<int:goal_id>")
@api_login_required
def api_update_goal(goal_id):
    user = current_user()
    goal = query_db("SELECT * FROM zero_waste_goals WHERE id = ? AND user_id = ?",
                    (goal_id, user["id"]), one=True)
    if not goal:
        return jsonify({"success": False, "error": "Goal not found."}), 404

    data = request.get_json(silent=True) or request.form
    was_completed = goal["status"] == "Completed"

    current_value = goal["current"]
    if data.get("current") is not None:
        try:
            current_value = max(float(data.get("current")), 0)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Enter a valid progress value."}), 400

    title = (data.get("title") or goal["title"]).strip()[:120]
    target = goal["target"]
    if data.get("target") is not None:
        target, error = positive_number(data.get("target"), "target")
        if error:
            return jsonify({"success": False, "error": error}), 400

    deadline = data.get("deadline", goal["deadline"]) or None
    status = _refresh_status({"current": current_value, "target": target, "deadline": deadline})

    execute_db(
        "UPDATE zero_waste_goals SET title = ?, target = ?, current = ?, deadline = ?, "
        "status = ? WHERE id = ?",
        (title, target, current_value, deadline, status, goal_id),
    )

    points = 0
    if status == "Completed" and not was_completed:
        points, _ = award_points(user["id"], "goal_complete")

    return jsonify({
        "success": True,
        "message": "Goal completed." if status == "Completed" else "Goal updated.",
        "status": status,
        "points_awarded": points,
    })


@goals_bp.delete("/api/goals/<int:goal_id>")
@api_login_required
def api_delete_goal(goal_id):
    user = current_user()
    goal = query_db("SELECT id FROM zero_waste_goals WHERE id = ? AND user_id = ?",
                    (goal_id, user["id"]), one=True)
    if not goal:
        return jsonify({"success": False, "error": "Goal not found."}), 404
    execute_db("DELETE FROM zero_waste_goals WHERE id = ?", (goal_id,))
    return jsonify({"success": True, "message": "Goal deleted."})
