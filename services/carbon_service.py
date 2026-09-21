"""
Carbon footprint estimation.

Every number produced here is an ESTIMATE built from the factors in config.py.
Nothing is hard-coded in the templates, so changing a factor changes the whole
application consistently.
"""

from config import EMISSION_FACTORS, RECYCLING_SAVINGS

WEEKS_PER_MONTH = 4.33
MONTHS_PER_YEAR = 12

VEHICLES = [
    {"value": "petrol_car", "label": "Petrol Car"},
    {"value": "diesel_car", "label": "Diesel Car"},
    {"value": "motorcycle", "label": "Motorcycle"},
    {"value": "bus", "label": "Bus"},
    {"value": "train", "label": "Train"},
    {"value": "bicycle", "label": "Bicycle"},
    {"value": "walking", "label": "Walking"},
]


def _num(value, default=0.0):
    """Parse a form value into a non-negative float."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return max(result, 0.0)


def calculate_footprint(payload):
    """
    Estimate a monthly carbon footprint from the calculator form.

    Expected keys: electricity, transport_type, transport_distance,
    veg_meals, nonveg_meals, plastic_waste, organic_waste, paper_waste.
    """
    electricity = _num(payload.get("electricity"))
    transport_type = payload.get("transport_type") or "walking"
    if transport_type not in EMISSION_FACTORS:
        transport_type = "walking"
    distance = _num(payload.get("transport_distance"))
    veg_meals = _num(payload.get("veg_meals"))
    nonveg_meals = _num(payload.get("nonveg_meals"))
    plastic = _num(payload.get("plastic_waste"))
    organic = _num(payload.get("organic_waste"))
    paper = _num(payload.get("paper_waste"))

    electricity_e = electricity * EMISSION_FACTORS["electricity"]
    transport_e = distance * EMISSION_FACTORS[transport_type]
    food_e = (
        veg_meals * EMISSION_FACTORS["meal_vegetarian"]
        + nonveg_meals * EMISSION_FACTORS["meal_non_vegetarian"]
    ) * WEEKS_PER_MONTH
    waste_e = (
        plastic * EMISSION_FACTORS["plastic"]
        + organic * EMISSION_FACTORS["organic"]
        + paper * EMISSION_FACTORS["paper"]
    )
    total = electricity_e + transport_e + food_e + waste_e

    breakdown = {
        "electricity": round(electricity_e, 2),
        "transport": round(transport_e, 2),
        "food": round(food_e, 2),
        "waste": round(waste_e, 2),
    }
    largest = max(breakdown, key=breakdown.get) if total > 0 else None

    return {
        "inputs": {
            "electricity": electricity,
            "transport_type": transport_type,
            "transport_distance": distance,
            "veg_meals": int(veg_meals),
            "nonveg_meals": int(nonveg_meals),
            "plastic_waste": plastic,
            "organic_waste": organic,
            "paper_waste": paper,
        },
        "breakdown": breakdown,
        "monthly_total": round(total, 2),
        "annual_total": round(total * MONTHS_PER_YEAR, 2),
        "largest_source": largest,
        "per_day": round(total / 30.0, 2),
        "trees_equivalent": round(total * MONTHS_PER_YEAR / 21.0, 1),  # ~21 kg CO2/tree/year
        "basis": "Estimated using configurable emission factors (see config.py).",
    }


def recycling_co2_saved(material, quantity_kg):
    """CO2e avoided by recycling `quantity_kg` of `material`."""
    factor = RECYCLING_SAVINGS.get((material or "other").strip().lower(), 0.5)
    return round(max(_num(quantity_kg), 0) * factor, 2)


def landfill_emissions(category, quantity_kg):
    """CO2e released if `quantity_kg` of `category` waste goes to landfill."""
    factor = EMISSION_FACTORS.get((category or "other").strip().lower(), 1.0)
    return round(max(_num(quantity_kg), 0) * factor, 2)


def factors_for_display():
    """Emission factors exposed to the UI so the page can show its own basis."""
    return {
        "electricity_kwh": EMISSION_FACTORS["electricity"],
        "vehicles": {v["label"]: EMISSION_FACTORS[v["value"]] for v in VEHICLES},
        "meal_vegetarian": EMISSION_FACTORS["meal_vegetarian"],
        "meal_non_vegetarian": EMISSION_FACTORS["meal_non_vegetarian"],
        "waste": {
            "plastic": EMISSION_FACTORS["plastic"],
            "paper": EMISSION_FACTORS["paper"],
            "organic": EMISSION_FACTORS["organic"],
        },
    }
