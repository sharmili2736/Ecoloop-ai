"""
EcoLoop AI — application entry point.

Run with:  python app.py
The database is created and seeded automatically on first start.
"""

import os
from datetime import timedelta

from flask import Flask, jsonify, redirect, render_template, request, url_for

from config import Config
from models.database import init_app, init_db, seed_demo_data
from routes import current_user
from routes.auth import auth_bp
from routes.biodiversity import biodiversity_bp
from routes.carbon import carbon_bp
from routes.challenges import challenges_bp
from routes.dashboard import dashboard_bp
from routes.goals import goals_bp
from routes.recycling import recycling_bp
from routes.reports import reports_bp
from routes.waste import waste_bp


def wants_json():
    """True when the caller is an API client rather than a browser page load."""
    return request.path.startswith("/api/") or \
        request.accept_mimetypes.best == "application/json"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(
        seconds=app.config["PERMANENT_SESSION_LIFETIME"])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    init_app(app)
    with app.app_context():
        init_db(app)
        seed_demo_data(app)

    for blueprint in (auth_bp, dashboard_bp, waste_bp, carbon_bp, recycling_bp,
                      goals_bp, biodiversity_bp, challenges_bp, reports_bp):
        app.register_blueprint(blueprint)

    # ----------------------------------------------------------------------- #
    # Landing page
    # ----------------------------------------------------------------------- #
    @app.route("/")
    def landing():
        return render_template("index.html", user=current_user())

    @app.context_processor
    def inject_globals():
        """Values every template can use without being passed explicitly."""
        return {
            "demo_email": app.config["DEMO_EMAIL"],
            "demo_password": app.config["DEMO_PASSWORD"],
            "signed_in": current_user() is not None,
        }

    # ----------------------------------------------------------------------- #
    # Error handling
    # ----------------------------------------------------------------------- #
    @app.errorhandler(400)
    def bad_request(_):
        if wants_json():
            return jsonify({"success": False, "error": "That request was not valid."}), 400
        return render_template("error.html", code=400,
                               message="That request was not valid."), 400

    @app.errorhandler(401)
    def unauthorised(_):
        if wants_json():
            return jsonify({"success": False, "error": "Sign in to continue."}), 401
        return redirect(url_for("auth.login_page"))

    @app.errorhandler(404)
    def not_found(_):
        if wants_json():
            return jsonify({"success": False, "error": "Not found."}), 404
        return render_template("error.html", code=404,
                               message="We could not find that page."), 404

    @app.errorhandler(413)
    def too_large(_):
        return jsonify({
            "success": False,
            "error": "That file is larger than the 5 MB limit.",
        }), 413

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception("Unhandled error: %s", error)
        if wants_json():
            return jsonify({"success": False,
                            "error": "Something went wrong. Please try again."}), 500
        return render_template("error.html", code=500,
                               message="Something went wrong. Please try again."), 500

    return app


app = create_app()


if __name__ == "__main__":
    print("\n  EcoLoop AI is running at http://127.0.0.1:5000")
    print(f"  Demo login: {Config.DEMO_EMAIL} / {Config.DEMO_PASSWORD}\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
