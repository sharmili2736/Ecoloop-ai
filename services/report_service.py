"""
Monthly sustainability report: data assembly plus an optional PDF export.

ReportLab is imported lazily so the application still starts and the HTML
report still works if the library is not installed.
"""

import calendar
import io
from datetime import datetime

from config import RECYCLING_SAVINGS
from models.database import query_db
from services.analytics_service import (
    month_bounds, sustainability_score, totals, waste_by_category,
)

try:  # Optional dependency, used only for PDF download.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the local environment
    REPORTLAB_AVAILABLE = False


def build_monthly_report(user, year, month):
    """Assemble every figure that appears on the report page."""
    user_id = user["id"]
    start, end = month_bounds(year, month)
    period = totals(user_id, start, end)
    lifetime = totals(user_id)

    carbon_row = query_db(
        "SELECT COALESCE(AVG(total_emissions), 0) AS avg_total, "
        "COALESCE(AVG(electricity_emissions), 0) AS elec, "
        "COALESCE(AVG(transport_emissions), 0) AS transport, "
        "COALESCE(AVG(food_emissions), 0) AS food, "
        "COALESCE(AVG(waste_emissions), 0) AS waste, COUNT(*) AS n "
        "FROM carbon_records WHERE user_id = ? AND created_at >= ? AND created_at < ?",
        (user_id, start, end), one=True)

    challenges = query_db(
        "SELECT c.title, c.points, uc.status, uc.progress FROM user_challenges uc "
        "JOIN challenges c ON c.id = uc.challenge_id WHERE uc.user_id = ? "
        "AND uc.joined_at < ? ORDER BY uc.status", (user_id, end))

    completed = [dict(c) for c in challenges if c["status"] == "Completed"]

    goals = query_db(
        "SELECT title, target, current, unit, status, deadline FROM zero_waste_goals "
        "WHERE user_id = ? ORDER BY status", (user_id,))

    observations = query_db(
        "SELECT species, category, location, observation_date FROM biodiversity_records "
        "WHERE user_id = ? AND created_at >= ? AND created_at < ? ORDER BY created_at DESC",
        (user_id, start, end))

    landfill_avoided = period["total_recycled"]
    score = sustainability_score(user_id)

    return {
        "period": {
            "year": year,
            "month": month,
            "label": f"{calendar.month_name[month]} {year}",
        },
        "user": {
            "name": user["name"],
            "email": user["email"],
            "organization": user["organization"] or "—",
            "user_type": user["user_type"],
            "eco_points": user["eco_points"],
        },
        "waste": {
            "generated": period["total_waste"],
            "recycled": period["total_recycled"],
            "plastic_recycled": period["plastic_recycled"],
            "recycling_rate": period["recycling_rate"],
            "by_material": period["recycled_by_material"],
            "categories": waste_by_category(user_id, months=1),
            "landfill_avoided": landfill_avoided,
        },
        "carbon": {
            "monthly_estimate": round(carbon_row["avg_total"], 2),
            "assessments": carbon_row["n"],
            "electricity": round(carbon_row["elec"], 2),
            "transport": round(carbon_row["transport"], 2),
            "food": round(carbon_row["food"], 2),
            "waste": round(carbon_row["waste"], 2),
            "co2_saved": period["co2_saved"],
        },
        "challenges": {
            "joined": len(challenges),
            "completed": completed,
            "points_from_challenges": sum(c["points"] for c in completed),
        },
        "goals": [dict(g) for g in goals],
        "biodiversity": {
            "count": len(observations),
            "records": [dict(o) for o in observations],
        },
        "score": score,
        "lifetime": lifetime,
        "generated_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        "basis": "All carbon figures are estimates from the emission factors in config.py.",
    }


def report_to_pdf(report):
    """Render a report dict to PDF bytes. Returns None if ReportLab is missing."""
    if not REPORTLAB_AVAILABLE:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=f"EcoLoop AI Report {report['period']['label']}",
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    green = colors.HexColor("#1d7a4c")
    heading = ParagraphStyle("Heading", parent=styles["Heading2"], textColor=green,
                             spaceBefore=14, spaceAfter=6, fontSize=13)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8.5,
                           textColor=colors.HexColor("#5b6b62"))

    story = [
        Paragraph("EcoLoop AI — Sustainability Report", ParagraphStyle(
            "Title", parent=styles["Title"], textColor=green, fontSize=20, spaceAfter=2)),
        Paragraph(report["period"]["label"], small),
        Spacer(1, 10),
    ]

    def table(rows, widths=(70 * mm, 95 * mm)):
        t = Table(rows, colWidths=widths, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#5b6b62")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#e2ece6")),
        ]))
        return t

    u = report["user"]
    story += [Paragraph("Account", heading), table([
        ["Name", u["name"]],
        ["Email", u["email"]],
        ["Organization", u["organization"]],
        ["User type", u["user_type"]],
        ["Eco points", f"{u['eco_points']:,}"],
    ])]

    w, c = report["waste"], report["carbon"]
    story += [Paragraph("Waste and recycling", heading), table([
        ["Waste generated", f"{w['generated']} kg"],
        ["Waste recycled", f"{w['recycled']} kg"],
        ["Plastic diverted", f"{w['plastic_recycled']} kg"],
        ["Recycling rate", f"{w['recycling_rate']}%"],
        ["Landfill avoided", f"{w['landfill_avoided']} kg"],
    ])]

    story += [Paragraph("Carbon footprint (estimated)", heading), table([
        ["Monthly estimate", f"{c['monthly_estimate']} kg CO2e"],
        ["Electricity", f"{c['electricity']} kg CO2e"],
        ["Transport", f"{c['transport']} kg CO2e"],
        ["Food", f"{c['food']} kg CO2e"],
        ["Waste", f"{c['waste']} kg CO2e"],
        ["CO2e avoided by recycling", f"{c['co2_saved']} kg"],
    ])]

    s = report["score"]
    story += [Paragraph(f"Sustainability score: {s['score']} / 100", heading),
              table([[k, f"{v} / 100"] for k, v in s["pillars"].items()])]

    story += [Paragraph("Activity", heading), table([
        ["Challenges joined", str(report["challenges"]["joined"])],
        ["Challenges completed", str(len(report["challenges"]["completed"]))],
        ["Biodiversity observations", str(report["biodiversity"]["count"])],
        ["Goals tracked", str(len(report["goals"]))],
    ])]

    story += [Spacer(1, 14), Paragraph(report["basis"], small),
              Paragraph(f"Generated {report['generated_at']} by EcoLoop AI.", small)]

    doc.build(story)
    buffer.seek(0)
    return buffer
