"""Eco Challenges: the gamification layer."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from models.database import execute_db, query_db, rows_to_list
from routes import api_login_required, award_points, current_user, login_required
from services.analytics_service import earned_badges

challenges_bp = Blueprint("challenges", __name__)


@challenges_bp.route("/challenges")
@login_required
def challenges_page():
    user = current_user()
    return render_template("challenges.html", user=user, active_page="challenges")


@challenges_bp.get("/api/challenges")
@api_login_required
def api_list_challenges():
    user = current_user()
    rows = query_db(
        "SELECT c.*, uc.progress, uc.status, uc.joined_at, uc.completed_at "
        "FROM challenges c LEFT JOIN user_challenges uc "
        "ON uc.challenge_id = c.id AND uc.user_id = ? ORDER BY c.id", (user["id"],))
    challenges = rows_to_list(rows)
    for c in challenges:
        c["joined"] = c["status"] is not None
        c["progress"] = c["progress"] or 0
        c["status"] = c["status"] or "Not joined"

    completed = [c for c in challenges if c["status"] == "Completed"]
    return jsonify({
        "success": True,
        "challenges": challenges,
        "summary": {
            "joined": sum(1 for c in challenges if c["joined"]),
            "completed": len(completed),
            "points_earned": sum(c["points"] for c in completed),
            "eco_points": user["eco_points"],
        },
        "badges": earned_badges(user["id"], user["eco_points"]),
    })


@challenges_bp.post("/api/challenges/<int:challenge_id>/join")
@api_login_required
def api_join_challenge(challenge_id):
    user = current_user()
    challenge = query_db("SELECT * FROM challenges WHERE id = ?", (challenge_id,), one=True)
    if not challenge:
        return jsonify({"success": False, "error": "Challenge not found."}), 404

    existing = query_db(
        "SELECT id FROM user_challenges WHERE user_id = ? AND challenge_id = ?",
        (user["id"], challenge_id), one=True)
    if existing:
        return jsonify({"success": False, "error": "You have already joined this challenge."}), 409

    execute_db(
        "INSERT INTO user_challenges (user_id, challenge_id, progress, status, joined_at) "
        "VALUES (?, ?, 0, 'Active', ?)",
        (user["id"], challenge_id, datetime.now().isoformat(timespec="seconds")),
    )
    return jsonify({"success": True,
                    "message": f"You joined “{challenge['title']}”."}), 201


@challenges_bp.put("/api/challenges/<int:challenge_id>/progress")
@api_login_required
def api_update_progress(challenge_id):
    user = current_user()
    entry = query_db(
        "SELECT uc.*, c.title, c.points FROM user_challenges uc "
        "JOIN challenges c ON c.id = uc.challenge_id "
        "WHERE uc.user_id = ? AND uc.challenge_id = ?",
        (user["id"], challenge_id), one=True)
    if not entry:
        return jsonify({"success": False, "error": "Join the challenge first."}), 404

    data = request.get_json(silent=True) or request.form
    try:
        progress = int(float(data.get("progress", entry["progress"])))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Enter a valid progress value."}), 400
    progress = max(0, min(progress, 100))

    was_completed = entry["status"] == "Completed"
    status = "Completed" if progress >= 100 else "Active"
    completed_at = (datetime.now().isoformat(timespec="seconds")
                    if status == "Completed" else None)

    execute_db(
        "UPDATE user_challenges SET progress = ?, status = ?, completed_at = ? "
        "WHERE user_id = ? AND challenge_id = ?",
        (progress, status, completed_at or entry["completed_at"], user["id"], challenge_id),
    )

    points = 0
    if status == "Completed" and not was_completed:
        # Award the challenge's own point value on top of the base completion bonus.
        execute_db("UPDATE users SET eco_points = eco_points + ? WHERE id = ?",
                   (entry["points"], user["id"]))
        points = entry["points"]

    refreshed = query_db("SELECT eco_points FROM users WHERE id = ?", (user["id"],), one=True)
    return jsonify({
        "success": True,
        "message": (f"Challenge completed. +{points} eco points."
                    if status == "Completed" and points else "Progress saved."),
        "status": status,
        "progress": progress,
        "points_awarded": points,
        "eco_points": refreshed["eco_points"],
        "completed": status == "Completed",
    })


@challenges_bp.delete("/api/challenges/<int:challenge_id>/leave")
@api_login_required
def api_leave_challenge(challenge_id):
    user = current_user()
    execute_db("DELETE FROM user_challenges WHERE user_id = ? AND challenge_id = ?",
               (user["id"], challenge_id))
    return jsonify({"success": True, "message": "You left the challenge."})
