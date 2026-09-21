"""
Central configuration for EcoLoop AI.

Everything that a reviewer or a future developer might want to tune
(emission factors, upload limits, database path) lives here instead of
being scattered through the codebase.
"""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Core Flask settings -------------------------------------------------
    # In production set ECOLOOP_SECRET_KEY as an environment variable.
    SECRET_KEY = os.environ.get("ECOLOOP_SECRET_KEY", "ecoloop-dev-secret-change-me")
    DATABASE = os.environ.get("ECOLOOP_DB", os.path.join(BASE_DIR, "database.db"))

    # --- File uploads --------------------------------------------------------
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB hard limit on any request body

    # --- Session -------------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days

    # --- Demo account --------------------------------------------------------
    DEMO_EMAIL = "demo@ecoloop.ai"
    DEMO_PASSWORD = "demo123"


# -----------------------------------------------------------------------------
# EMISSION FACTORS
# -----------------------------------------------------------------------------
# These are ESTIMATES used for educational purposes. They are rough averages
# drawn from commonly published public figures and are intentionally kept in
# one editable place so they can be swapped for region-specific values.
#
# Units:
#   electricity     -> kg CO2e per kWh
#   transport_*     -> kg CO2e per km travelled
#   meal_*          -> kg CO2e per meal
#   waste_*         -> kg CO2e per kg of waste sent to landfill
#   recycle_saving_*-> kg CO2e avoided per kg of material recycled
# -----------------------------------------------------------------------------
EMISSION_FACTORS = {
    # Grid electricity (India average grid intensity is used as the default)
    "electricity": 0.82,

    # Transport, per kilometre
    "petrol_car": 0.192,
    "diesel_car": 0.171,
    "motorcycle": 0.103,
    "bus": 0.089,
    "train": 0.041,
    "bicycle": 0.0,
    "walking": 0.0,

    # Food, per meal
    "meal_vegetarian": 0.72,
    "meal_non_vegetarian": 2.10,

    # Waste sent to landfill, per kg
    "plastic": 2.75,
    "paper": 1.05,
    "organic": 0.65,
    "glass": 0.85,
    "metal": 1.40,
    "e-waste": 2.10,
    "textile": 2.20,
    "other": 1.00,
}

# CO2e avoided for every kilogram of material that is recycled instead of
# being landfilled. Used by the recycling tracker and the dashboard.
RECYCLING_SAVINGS = {
    "plastic": 1.53,
    "paper": 0.89,
    "glass": 0.31,
    "metal": 3.56,
    "e-waste": 1.80,
    "textile": 1.10,
    "organic": 0.25,
    "other": 0.50,
}

# Points awarded for each type of eco action.
ECO_POINTS = {
    "waste_record": 5,
    "recycling_record": 10,
    "challenge_complete": 50,
    "biodiversity_record": 15,
    "carbon_assessment": 20,
    "goal_complete": 30,
}

# Badge thresholds; evaluated against a user's aggregated activity.
BADGES = [
    {"key": "eco_starter", "name": "Eco Starter", "icon": "seedling",
     "description": "Logged your first eco action.", "metric": "actions", "threshold": 1},
    {"key": "plastic_fighter", "name": "Plastic Fighter", "icon": "bottle-water",
     "description": "Recycled 25 kg of plastic.", "metric": "plastic_recycled", "threshold": 25},
    {"key": "recycling_hero", "name": "Recycling Hero", "icon": "recycle",
     "description": "Recycled 100 kg of material in total.", "metric": "total_recycled", "threshold": 100},
    {"key": "carbon_saver", "name": "Carbon Saver", "icon": "leaf",
     "description": "Avoided an estimated 100 kg of CO₂e.", "metric": "co2_saved", "threshold": 100},
    {"key": "biodiversity_guardian", "name": "Biodiversity Guardian", "icon": "dove",
     "description": "Recorded 10 species observations.", "metric": "observations", "threshold": 10},
    {"key": "zero_waste_champion", "name": "Zero-Waste Champion", "icon": "trophy",
     "description": "Earned 1,000 eco points.", "metric": "eco_points", "threshold": 1000},
]
