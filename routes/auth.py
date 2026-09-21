"""Authentication, profile and settings."""

import re
from datetime import datetime

from flask import (
    Blueprint, jsonify, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from models.database import execute_db, query_db
from routes import api_login_required, current_user, login_required
from services.analytics_service import earned_badges, sustainability_score

auth_bp = Blueprint("auth", __name__)

USER_TYPES = ["Student", "Faculty", "Individual", "Organization"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
@auth_bp.route("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/register")
def register_page():
    if current_user():
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("register.html", user_types=USER_TYPES)


@auth_bp.route("/logout")
def logout_page():
    session.clear()
    return redirect(url_for("landing"))


@auth_bp.route("/profile")
@login_required
def profile_page():
    user = current_user()
    return render_template(
        "profile.html",
        user=user,
        active_page="profile",
        user_types=USER_TYPES,
        score=sustainability_score(user["id"]),
        badges=earned_badges(user["id"], user["eco_points"]),
    )


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
@auth_bp.post("/api/register")
def api_register():
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    organization = (data.get("organization") or "").strip()
    user_type = (data.get("user_type") or "Individual").strip()

    if len(name) < 2:
        return jsonify({"success": False, "error": "Enter your full name."}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"success": False, "error": "Enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"success": False, "error": "Use a password of at least 6 characters."}), 400
    if user_type not in USER_TYPES:
        return jsonify({"success": False, "error": "Choose a valid user type."}), 400

    if query_db("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return jsonify({"success": False, "error": "That email is already registered."}), 409

    user_id = execute_db(
        "INSERT INTO users (name, email, password_hash, organization, user_type, "
        "eco_points, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (name, email, generate_password_hash(password), organization, user_type,
         datetime.now().isoformat(timespec="seconds")),
    )

    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    return jsonify({
        "success": True,
        "message": f"Welcome to EcoLoop, {name.split()[0]}.",
        "redirect": url_for("dashboard.dashboard_page"),
    }), 201


@auth_bp.post("/api/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Enter your email and password."}), 400

    user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Incorrect email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify({
        "success": True,
        "message": f"Signed in as {user['name']}.",
        "redirect": url_for("dashboard.dashboard_page"),
    })


@auth_bp.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"success": True, "redirect": url_for("landing")})


@auth_bp.get("/api/profile")
@api_login_required
def api_profile():
    user = current_user()
    return jsonify({
        "success": True,
        "profile": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "organization": user["organization"],
            "user_type": user["user_type"],
            "eco_points": user["eco_points"],
            "theme": user["theme"],
            "notifications": bool(user["notifications"]),
            "created_at": user["created_at"],
        },
        "score": sustainability_score(user["id"]),
        "badges": earned_badges(user["id"], user["eco_points"]),
    })


@auth_bp.put("/api/profile")
@api_login_required
def api_update_profile():
    user = current_user()
    data = request.get_json(silent=True) or request.form
    name = (data.get("name") or user["name"]).strip()
    organization = (data.get("organization") or "").strip()
    user_type = (data.get("user_type") or user["user_type"]).strip()
    theme = (data.get("theme") or user["theme"]).strip()
    notifications = 1 if str(data.get("notifications", user["notifications"])).lower() in ("1", "true", "on", "yes") else 0

    if len(name) < 2:
        return jsonify({"success": False, "error": "Enter your full name."}), 400
    if user_type not in USER_TYPES:
        return jsonify({"success": False, "error": "Choose a valid user type."}), 400
    if theme not in ("light", "dark"):
        theme = "light"

    execute_db(
        "UPDATE users SET name = ?, organization = ?, user_type = ?, theme = ?, "
        "notifications = ? WHERE id = ?",
        (name, organization, user_type, theme, notifications, user["id"]),
    )
    return jsonify({"success": True, "message": "Profile updated."})


@auth_bp.put("/api/profile/password")
@api_login_required
def api_change_password():
    user = current_user()
    data = request.get_json(silent=True) or request.form
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not check_password_hash(user["password_hash"], current_password):
        return jsonify({"success": False, "error": "Your current password is incorrect."}), 401
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "Use a new password of at least 6 characters."}), 400

    execute_db("UPDATE users SET password_hash = ? WHERE id = ?",
               (generate_password_hash(new_password), user["id"]))
    return jsonify({"success": True, "message": "Password changed."})
