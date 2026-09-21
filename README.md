# 🌱 EcoLoop AI — Intelligent Circular Waste & Carbon Management System

A full-stack sustainability dashboard for students, colleges, offices and small
organisations. Log waste, estimate your carbon footprint, track recycling, set zero-waste
goals, record biodiversity observations, complete eco challenges and export a monthly
sustainability report.

Built with **Flask + SQLite + vanilla JavaScript + Chart.js**. No React, no Node backend,
no hardware, no paid APIs. It runs locally with one command.

---

## 1. Problem statement

Campuses and small organisations already produce sustainability data — bins get weighed,
recycling gets handed over, electricity bills arrive every month, students notice birds and
trees on campus. That data sits in notebooks, WhatsApp groups and spreadsheets, in
different formats, owned by different people. Nobody can answer the two questions that
matter: *where is our biggest impact, and what should we do next?*

## 2. Solution

EcoLoop AI puts all of it into one account-based dashboard and turns the numbers into
prioritised actions:

- Every record is stored in a single SQLite database against a user.
- A carbon engine converts electricity, travel, food and waste into estimated CO₂e using
  factors that a reviewer can read and edit.
- A rule engine reads the user's own numbers and emits recommendations that quote those
  numbers back, so nothing is a black box.
- A five-pillar sustainability score turns the whole picture into a single 0–100 figure.

## 3. Features

| Module | What it does |
|---|---|
| Landing page | Hero, feature cards, four-step process, animated impact counters |
| Authentication | Register, login, logout, hashed passwords, session-protected routes |
| Dashboard | Four animated stat cards, circular sustainability score with pillar breakdown, data-driven insight, four Chart.js charts, goals, challenges, biodiversity summary, recommendations |
| Waste Analyzer | Drag-and-drop image upload, material classification, confidence ring, impact estimate, saved records with search/category/date filters |
| Carbon Calculator | Electricity, transport, food and waste inputs; monthly and annual estimate; donut breakdown; comparison with the previous assessment; history chart |
| Recycling Tracker | Material/quantity/method/date/notes records, material goals with progress bars, two charts, filters |
| Zero-Waste Planner | Goal CRUD, progress updates, automatic Active/Completed/Overdue status, status filters |
| Biodiversity Monitor | Species observations with optional photo, statistics, category doughnut, stylised pin map (no GPS or external map service) |
| Eco Challenges | Six seeded challenges, join, progress slider, completion awards, six achievement badges |
| Eco Points | Points for every action, shown live in the top bar |
| Reports | Monthly report for any month, print-friendly view, PDF download via ReportLab |
| Profile & Settings | Update profile, change password, light/dark theme, notification preference, score breakdown, badges |

Plus, throughout: toasts, modals, confirmation dialogs, skeleton loaders, empty states,
animated counters and progress bars, keyboard focus styles, ARIA labels, and a layout that
works from a 360 px phone up to a wide desktop (the sidebar collapses to a hamburger menu
below 860 px).

## 4. Technology stack

- **Frontend:** HTML5, CSS3 (custom properties, grid, flexbox, glassmorphism), vanilla JS
- **Charts:** Chart.js 4 (CDN)
- **Icons:** Font Awesome 6 (CDN)
- **Fonts:** Inter (Google Fonts)
- **Backend:** Python 3.9+, Flask 3, blueprints
- **Auth:** Flask sessions + Werkzeug `generate_password_hash` / `check_password_hash`
- **Database:** SQLite 3 (standard library `sqlite3`, parameterised queries only)
- **PDF:** ReportLab (optional — everything else works without it)

An internet connection is needed on first page load for the three CDN assets. Everything
else, including all data and the classifier, runs locally.

## 5. Folder structure

```
ecoloop-ai/
├── app.py                      # application factory, landing route, error handlers
├── config.py                   # settings, EMISSION_FACTORS, points, badges
├── requirements.txt
├── database.db                 # created automatically on first run
│
├── models/
│   └── database.py             # schema, connection handling, demo data seeding
│
├── services/
│   ├── ai_service.py           # demo waste classifier + insight generator
│   ├── carbon_service.py       # footprint calculation from emission factors
│   ├── analytics_service.py    # aggregates, monthly series, sustainability score
│   ├── recommendation_service.py
│   └── report_service.py       # monthly report data + ReportLab PDF
│
├── routes/
│   ├── __init__.py             # login_required, validation, uploads, eco points
│   ├── auth.py                 # register / login / logout / profile
│   ├── dashboard.py
│   ├── waste.py
│   ├── carbon.py
│   ├── recycling.py
│   ├── goals.py                # zero-waste planner
│   ├── biodiversity.py
│   ├── challenges.py
│   └── reports.py
│
├── templates/
│   ├── base.html               # sidebar + topbar shell for signed-in pages
│   ├── index.html  login.html  register.html
│   ├── dashboard.html  waste.html  carbon.html  recycling.html
│   ├── zero_waste.html  biodiversity.html  challenges.html
│   ├── reports.html  report_print.html  profile.html
│   └── error.html
│
├── static/
│   ├── css/style.css
│   ├── js/
│   │   ├── main.js             # API wrapper, toasts, modals, sidebar, search
│   │   ├── animations.js       # counters, bars, rings, scroll reveals
│   │   ├── charts.js           # Chart.js factories with shared theme
│   │   ├── dashboard.js  waste.js  carbon.js  recycling.js
│   │   ├── zero_waste.js  biodiversity.js  challenges.js
│   │   └── reports.js  profile.js
│   └── uploads/                # user-uploaded images
│
└── README.md
```

## 6. Installation

### Step 1 — get the project and open the folder

```bash
cd ecoloop-ai
```

### Step 2 — create a virtual environment

```bash
python -m venv venv
```

Activate it:

```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (cmd)
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### Step 3 — install the requirements

```bash
pip install -r requirements.txt
```

### Step 4 — initialise the database

Nothing to do. On the first run `app.py` creates `database.db`, builds every table, seeds
the six challenges and creates the demo account with six months of realistic activity.

To start over, delete `database.db` and run the app again.

### Step 5 — run it

```bash
python app.py
```

Open **http://127.0.0.1:5000**.

## 7. Demo credentials

```
Email:    demo@ecoloop.ai
Password: demo123
```

The login page has a **Fill demo details** button. The demo account arrives with waste
records, recycling handovers, six monthly carbon assessments, five goals, twelve
biodiversity observations, joined challenges and 1,280 eco points, so the dashboard is
populated the moment you sign in.

## 8. AI architecture — what is real and what is not

**The classifier in this build is a rule-based demo, not a trained model.** It is labelled
that way in the UI, in the API response (`"mode": "demo"`) and in the code. It decides a
label from the category you select, keywords in the uploaded file name, and a deterministic
hash of the file so the same image always returns the same confidence. The confidence
percentage is a *simulated* value.

The application only ever calls three functions, all in `services/ai_service.py`:

```python
def classify_waste(image_path=None, selected_category=None): ...
def estimate_impact(result, quantity_kg): ...
def generate_sustainability_insight(user_data): ...
```

### Replacing the demo classifier with a real model

Open `services/ai_service.py`, set `MODEL_AVAILABLE = True`, and fill in
`_predict_from_model()`, which must return `(material_label, confidence_float)`:

```python
import tensorflow as tf
_model = tf.keras.models.load_model("models/waste_cnn.keras")
LABELS = ["Plastic Bottle", "Cardboard Box", "Aluminium Can", ...]

def _predict_from_model(image_path):
    img = tf.keras.utils.load_img(image_path, target_size=(224, 224))
    arr = tf.keras.utils.img_to_array(img)[None, ...] / 255.0
    probs = _model.predict(arr)[0]
    idx = int(probs.argmax())
    return LABELS[idx], float(probs[idx])
```

No route, template or JavaScript file has to change. The same hook works for a PyTorch
model or a hosted vision API.

The insight and recommendation engines are deliberately rule-based so that every sentence
they produce can be traced to a stored number. To swap in an LLM, replace `_rule_set()` in
`services/recommendation_service.py`.

## 9. Carbon calculation

All emission factors live in one dictionary in `config.py`:

```python
EMISSION_FACTORS = {
    "electricity": 0.82,      # kg CO2e per kWh
    "petrol_car": 0.192,      # kg CO2e per km
    "diesel_car": 0.171,
    "motorcycle": 0.103,
    "bus": 0.089,
    "train": 0.041,
    "bicycle": 0.0,
    "walking": 0.0,
    "meal_vegetarian": 0.72,  # kg CO2e per meal
    "meal_non_vegetarian": 2.10,
    "plastic": 2.75,          # kg CO2e per kg landfilled
    "paper": 1.05,
    "organic": 0.65,
    ...
}
```

The monthly estimate is:

```
electricity_kWh × factor
+ distance_km × vehicle_factor
+ (veg_meals × veg_factor + nonveg_meals × nonveg_factor) × 4.33 weeks
+ Σ (waste_kg × waste_factor)
```

Annual figures are the monthly total × 12. `RECYCLING_SAVINGS` holds the CO₂e avoided per
kilogram recycled and drives the "CO₂ saved" figures.

These are **rough averages for education, not an audited inventory**, which is why the UI
says "Estimated carbon footprint based on configurable emission factors" and the calculator
page has a button that shows every factor currently in use. Change the values in
`config.py` to match your region and the whole application follows.

### Sustainability score

Five pillars, each scored 0–100 and equally weighted: Waste Management, Recycling, Carbon
Reduction, Eco Actions, Biodiversity. The logic is in
`services/analytics_service.py → sustainability_score()`.

## 10. API endpoints

All return JSON with a `success` flag and proper status codes (200, 201, 400, 401, 404,
409, 413, 500).

```
POST   /api/register                        POST   /api/login          POST /api/logout
GET    /api/profile    PUT /api/profile     PUT    /api/profile/password

GET    /api/dashboard                       GET    /api/recommendations

GET    /api/waste      POST /api/waste      DELETE /api/waste/<id>
POST   /api/waste/analyze

GET    /api/carbon                          POST   /api/carbon/calculate

GET    /api/recycling  POST /api/recycling  DELETE /api/recycling/<id>

GET    /api/goals      POST /api/goals      PUT /api/goals/<id>   DELETE /api/goals/<id>

GET    /api/biodiversity   POST /api/biodiversity   DELETE /api/biodiversity/<id>

GET    /api/challenges     POST /api/challenges/<id>/join
PUT    /api/challenges/<id>/progress        DELETE /api/challenges/<id>/leave

GET    /api/reports/monthly?year=&month=
GET    /reports/print?year=&month=           GET /reports/download?year=&month=
```

## 11. Database schema

`users`, `waste_records`, `carbon_records`, `recycling_records`, `zero_waste_goals`,
`biodiversity_records`, `challenges`, `user_challenges`, `recommendations` — defined in
`models/database.py` with foreign keys and `ON DELETE CASCADE`.

## 12. Security

- Passwords stored only as Werkzeug PBKDF2 hashes; plain text is never written anywhere.
- Session-based auth with `HttpOnly` and `SameSite=Lax` cookies.
- `@login_required` redirects anonymous page visitors; `@api_login_required` returns 401
  for JSON endpoints.
- Every SQL statement is parameterised — no string interpolation anywhere.
- Uploads are validated by extension, renamed with a UUID via `secure_filename`, and capped
  at 5 MB (`MAX_CONTENT_LENGTH`, with a 413 handler).
- All user input is validated server-side; the browser-side checks are a convenience only.
- Every user query is scoped by `user_id`, so one account cannot read or delete another's
  records.
- `SECRET_KEY` and the database path read from environment variables
  (`ECOLOOP_SECRET_KEY`, `ECOLOOP_DB`) when set.

Before any real deployment: set a strong `ECOLOOP_SECRET_KEY`, run `app.run(debug=False)`
behind a WSGI server such as gunicorn or waitress, and serve over HTTPS.

## 13. Accessibility

Semantic landmarks, a skip link, labels on every control, visible focus rings, ARIA
attributes on modals, dropdowns and live regions, colour contrast that passes on both
themes, and `prefers-reduced-motion` support that disables all animation.

## 14. Future enhancements

1. Train and ship a real waste-classification CNN, replacing the demo hook.
2. Replace the rule engine with an LLM that drafts recommendations from the same data.
3. Organisation accounts with shared dashboards and department-level leaderboards.
4. Region-specific emission factor packs loaded from a data file.
5. Optional GPS and a real map layer for biodiversity records.
6. CSV/Excel import for existing waste and utility logs.
7. Email or push reminders for goal deadlines and challenge check-ins.
8. Offline-first PWA so records can be captured in the field.

---

Built as a Student Innovation project — Open Clean Tech & Sustainable Development.
