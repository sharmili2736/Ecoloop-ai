"""
EcoLoop AI - Shared helpers used by every blueprint.

Keeps authentication, upload validation and input parsing in one place so the
route modules stay small and readable.
"""

import os
import re
import uuid
from functools import wraps

from flask import current_app, jsonify, redirect, request, session, url_for
from werkzeug.utils import secure_filename

from models.database import query_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def login_required(view):
    """Protect a route. HTML routes redirect, /api routes return JSON 401."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required."}), 401
            return redirect(url_for("auth.login_page", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def current_user():
    """Return the logged-in user row as a dict, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)


def current_user_id():
    return session.get("user_id")


# ---------------------------------------------------------------------------
# Input parsing / validation
# ---------------------------------------------------------------------------
def payload():
    """Read JSON or form data transparently."""
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form.to_dict()


def parse_float(value, field_name="value", minimum=None, required=True):
    """Return (number, error_message)."""
    if value in (None, ""):
        if required:
            return None, f"Please enter a valid {field_name}."
        return 0.0, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, f"Please enter a valid numeric {field_name}."
    if minimum is not None and number < minimum:
        return None, f"Please enter a valid positive {field_name}."
    return number, None


def valid_email(email):
    return bool(EMAIL_RE.match((email or "").strip()))


def json_error(message, status=400):
    return jsonify({"success": False, "error": message}), status


# ---------------------------------------------------------------------------
# File uploads
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return ("." in filename
            and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"])


def save_upload(file_storage):
    """
    Validate and store an uploaded image.

    Returns (relative_path, original_filename, error_message).
    `relative_path` is relative to /static so templates can use url_for.
    """
    if not file_storage or not file_storage.filename:
        return None, None, None  # nothing uploaded - this is allowed

    original = secure_filename(file_storage.filename)
    if not original or not allowed_file(original):
        allowed = ", ".join(sorted(current_app.config["ALLOWED_EXTENSIONS"]))
        return None, None, f"Please upload a supported image format ({allowed})."

    extension = original.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    file_storage.save(os.path.join(folder, stored_name))
    return f"uploads/{stored_name}", original, None
