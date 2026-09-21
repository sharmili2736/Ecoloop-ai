"""
Shared helpers for every blueprint: authentication guards, input validation,
safe file uploads and the eco-points ledger.
"""

import os
import uuid
from functools import wraps

from flask import current_app, jsonify, redirect, session, url_for
from werkzeug.utils import secure_filename

from config import ECO_POINTS
from models.database import execute_db, query_db


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
def current_user():
    """Return the logged-in user row, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)


def login_required(view):
    """Protect an HTML page: redirect anonymous visitors to the login page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            session.clear()
            return redirect(url_for("auth.login_page", next_page="1"))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """Protect a JSON endpoint: return 401 instead of redirecting."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"success": False, "error": "Sign in to continue."}), 401
        return view(*args, **kwargs)
    return wrapped


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def positive_number(value, field="quantity"):
    """Validate a positive number. Returns (value, error_message)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"Enter a valid {field}."
    if number <= 0:
        return None, f"Enter a {field} greater than zero."
    if number > 1_000_000:
        return None, f"That {field} looks too large. Check the value and try again."
    return round(number, 3), None


def required_text(value, field, max_length=200):
    value = (value or "").strip()
    if not value:
        return None, f"{field} is required."
    if len(value) > max_length:
        return None, f"{field} must be under {max_length} characters."
    return value, None


def one_of(value, allowed, field):
    value = (value or "").strip()
    match = next((a for a in allowed if a.lower() == value.lower()), None)
    if match is None:
        return None, f"Choose a valid {field}."
    return match, None


# --------------------------------------------------------------------------- #
# Uploads
# --------------------------------------------------------------------------- #
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


def save_upload(file_storage):
    """
    Validate and store an uploaded image.
    Returns (relative_path, error_message); both None means no file was sent.
    """
    if file_storage is None or not file_storage.filename:
        return None, None
    if not allowed_file(file_storage.filename):
        return None, "Upload a PNG, JPG, GIF or WEBP image."

    original = secure_filename(file_storage.filename)
    extension = original.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}_{original[:40]}"
    if not stored_name.lower().endswith(extension):
        stored_name = f"{stored_name}.{extension}"

    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, stored_name))
    return f"uploads/{stored_name}", None


# --------------------------------------------------------------------------- #
# Eco points
# --------------------------------------------------------------------------- #
def award_points(user_id, action):
    """Add points for an eco action and return the new total."""
    points = ECO_POINTS.get(action, 0)
    if points:
        execute_db("UPDATE users SET eco_points = eco_points + ? WHERE id = ?",
                   (points, user_id))
    row = query_db("SELECT eco_points FROM users WHERE id = ?", (user_id,), one=True)
    return points, (row["eco_points"] if row else 0)
