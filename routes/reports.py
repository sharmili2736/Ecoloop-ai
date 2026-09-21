"""Sustainability reports: JSON API, print-friendly page and PDF download."""

from datetime import datetime

from flask import Blueprint, jsonify, render_template, request, send_file

from routes import api_login_required, current_user, login_required
from services.report_service import (
    REPORTLAB_AVAILABLE, build_monthly_report, report_to_pdf,
)

reports_bp = Blueprint("reports", __name__)


def _period_from_request():
    now = datetime.now()
    try:
        year = int(request.args.get("year", now.year))
        month = int(request.args.get("month", now.month))
    except ValueError:
        return None, None, "Choose a valid month and year."
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return None, None, "Choose a valid month and year."
    return year, month, None


@reports_bp.route("/reports")
@login_required
def reports_page():
    user = current_user()
    now = datetime.now()
    return render_template(
        "reports.html",
        user=user,
        active_page="reports",
        current_year=now.year,
        current_month=now.month,
        years=list(range(now.year, now.year - 4, -1)),
        pdf_available=REPORTLAB_AVAILABLE,
    )


@reports_bp.get("/api/reports/monthly")
@api_login_required
def api_monthly_report():
    year, month, error = _period_from_request()
    if error:
        return jsonify({"success": False, "error": error}), 400
    report = build_monthly_report(current_user(), year, month)
    return jsonify({"success": True, "report": report, "pdf_available": REPORTLAB_AVAILABLE})


@reports_bp.route("/reports/print")
@login_required
def print_report():
    year, month, error = _period_from_request()
    if error:
        year, month = datetime.now().year, datetime.now().month
    report = build_monthly_report(current_user(), year, month)
    return render_template("report_print.html", report=report, user=current_user())


@reports_bp.route("/reports/download")
@login_required
def download_report():
    year, month, error = _period_from_request()
    if error:
        year, month = datetime.now().year, datetime.now().month

    report = build_monthly_report(current_user(), year, month)
    buffer = report_to_pdf(report)
    if buffer is None:
        return jsonify({
            "success": False,
            "error": "PDF export needs ReportLab. Run: pip install reportlab, "
                     "or use the print view instead.",
        }), 503

    filename = f"ecoloop-report-{year}-{month:02d}.pdf"
    return send_file(buffer, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)
