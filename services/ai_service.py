"""
AI service for EcoLoop AI.

=============================================================================
HONEST DESCRIPTION OF WHAT THIS DOES TODAY
=============================================================================
`classify_waste()` in this build is a RULE-BASED DEMO CLASSIFIER. It does not
run a neural network and it does not look at pixels. It decides a label from:

    1. the category the user selected in the form (trusted first), and
    2. keywords found in the uploaded file name, and
    3. a small deterministic hash of the file so repeated uploads of the same
       image always return the same confidence value.

The confidence number it returns is therefore a SIMULATED confidence, not a
softmax probability. The UI labels it as demo output, and so does this file.

=============================================================================
HOW TO PLUG IN A REAL MODEL LATER
=============================================================================
Replace the body of `_predict_from_model()` with a real inference call and set
MODEL_AVAILABLE = True. The rest of the application only ever calls
`classify_waste()`, so nothing else has to change. For example:

    import tensorflow as tf
    _model = tf.keras.models.load_model("models/waste_cnn.keras")

    def _predict_from_model(image_path):
        img = tf.keras.utils.load_img(image_path, target_size=(224, 224))
        arr = tf.keras.utils.img_to_array(img)[None, ...] / 255.0
        probs = _model.predict(arr)[0]
        idx = int(probs.argmax())
        return CLASS_NAMES[idx], float(probs[idx])

The same idea works for a PyTorch model or a hosted vision API.
"""

import hashlib
import os

# Flip this to True once a real model is wired into _predict_from_model().
MODEL_AVAILABLE = False

# Class labels the demo classifier can produce, grouped by waste category.
CLASS_NAMES = {
    "Plastic": ["Plastic Bottle", "Plastic Bag", "Food Container", "Plastic Wrapper"],
    "Paper": ["Cardboard Box", "Newspaper", "Office Paper", "Paper Cup"],
    "Glass": ["Glass Bottle", "Glass Jar", "Broken Glassware"],
    "Metal": ["Aluminium Can", "Steel Tin", "Metal Scrap"],
    "Organic": ["Food Scraps", "Vegetable Peels", "Garden Waste"],
    "E-Waste": ["Mobile Charger", "Circuit Board", "Battery"],
    "Textile": ["Cotton Fabric", "Worn Clothing", "Synthetic Cloth"],
    "Other": ["Mixed Waste", "Unidentified Item"],
}

# Filename keywords -> category. Used only in demo mode.
KEYWORD_MAP = {
    "Plastic": ["plastic", "bottle", "pet", "polythene", "wrapper", "packet", "straw"],
    "Paper": ["paper", "cardboard", "carton", "news", "book", "box"],
    "Glass": ["glass", "jar", "bulb", "mirror"],
    "Metal": ["metal", "can", "tin", "aluminium", "aluminum", "steel", "iron"],
    "Organic": ["organic", "food", "veg", "fruit", "leaf", "leaves", "compost", "peel"],
    "E-Waste": ["ewaste", "e-waste", "electronic", "battery", "charger", "phone", "laptop", "circuit"],
    "Textile": ["cloth", "textile", "fabric", "shirt", "cotton", "jeans"],
}

# Guidance shown next to each result.
CATEGORY_GUIDE = {
    "Plastic": {
        "label": "Recyclable Plastic",
        "action": "Rinse the item, dry it, and send it to a plastic recycling stream.",
        "recyclable_share": 0.85,
    },
    "Paper": {
        "label": "Recyclable Paper",
        "action": "Keep it dry and free of food residue, then bundle it for paper recycling.",
        "recyclable_share": 0.90,
    },
    "Glass": {
        "label": "Recyclable Glass",
        "action": "Remove lids, rinse, and hand over to a glass collection point.",
        "recyclable_share": 0.95,
    },
    "Metal": {
        "label": "Recyclable Metal",
        "action": "Crush cans to save space and give them to a scrap collector.",
        "recyclable_share": 0.95,
    },
    "Organic": {
        "label": "Compostable Organic",
        "action": "Add it to a compost pit or a community composting service.",
        "recyclable_share": 0.80,
    },
    "E-Waste": {
        "label": "Hazardous E-Waste",
        "action": "Never bin this. Drop it at an authorised e-waste collection centre.",
        "recyclable_share": 0.70,
    },
    "Textile": {
        "label": "Reusable Textile",
        "action": "Donate wearable items; send worn-out cloth to a textile recycler.",
        "recyclable_share": 0.60,
    },
    "Other": {
        "label": "Mixed / Needs Sorting",
        "action": "Separate this into its material parts before deciding where it goes.",
        "recyclable_share": 0.30,
    },
}

# Rough kg CO2e avoided per kg of material diverted from landfill.
DIVERSION_SAVINGS = {
    "Plastic": 1.53, "Paper": 0.89, "Glass": 0.31, "Metal": 3.56,
    "Organic": 0.25, "E-Waste": 1.80, "Textile": 1.10, "Other": 0.50,
}


# --------------------------------------------------------------------------- #
# Replaceable model hook
# --------------------------------------------------------------------------- #
def _predict_from_model(image_path):
    """
    REPLACE ME with real inference.

    Should return a (material_label, confidence_float) tuple.
    Returning None tells classify_waste() to fall back to the demo classifier.
    """
    return None


# --------------------------------------------------------------------------- #
# Demo classifier
# --------------------------------------------------------------------------- #
def _category_from_filename(image_path):
    """Guess a category from keywords in the file name. Demo logic only."""
    if not image_path:
        return None
    name = os.path.basename(image_path).lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(keyword in name for keyword in keywords):
            return category
    return None


def _stable_choice(seed_text, options):
    """Pick an option deterministically so the same input gives the same answer."""
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return options[int(digest[:8], 16) % len(options)]


def _stable_confidence(seed_text, low=0.72, high=0.96):
    digest = hashlib.sha256(("conf" + seed_text).encode("utf-8")).hexdigest()
    span = high - low
    return round(low + (int(digest[8:16], 16) % 1000) / 1000 * span, 2)


def classify_waste(image_path=None, selected_category=None):
    """
    Return a classification result for an uploaded waste image.

    Args:
        image_path: path to the uploaded file, or None if the user only
                    picked a category.
        selected_category: category chosen by the user in the form.

    Returns a dict consumed directly by the Waste Analyzer page.
    """
    mode = "demo"
    material = None
    confidence = None

    # 1. Real model first, when one is available.
    if MODEL_AVAILABLE and image_path:
        prediction = _predict_from_model(image_path)
        if prediction:
            material, confidence = prediction
            mode = "model"

    # 2. Demo path.
    if material is None:
        category = (selected_category or "").strip().title()
        if category not in CATEGORY_GUIDE:
            category = _category_from_filename(image_path) or "Other"
        seed = os.path.basename(image_path) if image_path else category
        material = _stable_choice(seed + category, CLASS_NAMES[category])
        confidence = _stable_confidence(seed + category)
    else:
        category = next(
            (cat for cat, items in CLASS_NAMES.items() if material in items), "Other"
        )

    guide = CATEGORY_GUIDE[category]
    return {
        "mode": mode,  # "demo" until a real model is wired in
        "category": category,
        "material": material,
        "confidence": round(confidence * 100, 1),
        "classification": guide["label"],
        "action": guide["action"],
        "recyclable_share": guide["recyclable_share"],
        "co2_per_kg": DIVERSION_SAVINGS[category],
        "note": (
            "Demo classifier: result derived from the selected category and file name, "
            "not from image pixels."
            if mode == "demo" else "Prediction from the loaded model."
        ),
    }


def estimate_impact(result, quantity_kg):
    """Turn a classification plus a weight into the impact numbers shown in the UI."""
    quantity_kg = max(float(quantity_kg or 0), 0)
    recyclable = round(quantity_kg * result["recyclable_share"], 2)
    return {
        "recyclable_weight": recyclable,
        "landfill_diverted": recyclable,
        "co2_saved": round(recyclable * result["co2_per_kg"], 2),
        "landfill_remaining": round(quantity_kg - recyclable, 2),
    }


def generate_sustainability_insight(user_data):
    """
    Produce one short, data-driven sentence for the dashboard insight card.
    Rule-based on purpose: every claim can be traced back to a stored number.
    """
    recycling_rate = user_data.get("recycling_rate", 0)
    recyclable_change = user_data.get("recyclable_change_pct", 0)
    top_category = user_data.get("top_waste_category")
    carbon_change = user_data.get("carbon_change_pct", 0)
    total_waste = user_data.get("total_waste", 0)

    if total_waste == 0:
        return ("No waste entries yet. Log a week of waste and EcoLoop will start "
                "showing you where your biggest reductions are.")

    if recyclable_change >= 10:
        return (f"Your recyclable waste rose {recyclable_change:.0f}% this month. "
                f"Separating plastic and paper at source would push more of it "
                f"into recycling instead of landfill.")

    if recycling_rate < 35:
        return (f"You are recycling {recycling_rate:.0f}% of what you throw away. "
                f"Most of the gap is {top_category or 'mixed'} waste, which is the "
                f"easiest place to start sorting.")

    if carbon_change <= -5:
        return (f"Your estimated footprint fell {abs(carbon_change):.0f}% versus last "
                f"month. Electricity and travel are driving that drop, so keep those "
                f"habits going.")

    if carbon_change >= 10:
        return (f"Your estimated footprint climbed {carbon_change:.0f}% this month. "
                f"Check your electricity units and travel distance first, since they "
                f"usually account for most of a monthly increase.")

    return (f"You are recycling {recycling_rate:.0f}% of your waste, which is above "
            f"average for a campus user. Composting your organic share would lift "
            f"that further.")
