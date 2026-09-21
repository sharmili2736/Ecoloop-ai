"""
SQLite access layer.

All queries in the project go through `query_db` / `execute_db`, which use
parameterised statements only. String formatting is never used to build SQL,
which is what keeps the app free of injection holes.
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    organization  TEXT,
    user_type     TEXT NOT NULL DEFAULT 'Individual',
    eco_points    INTEGER NOT NULL DEFAULT 0,
    theme         TEXT NOT NULL DEFAULT 'light',
    notifications INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS waste_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    category    TEXT NOT NULL,
    material    TEXT,
    quantity    REAL NOT NULL,
    unit        TEXT NOT NULL DEFAULT 'kg',
    image_path  TEXT,
    ai_result   TEXT,
    confidence  REAL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS carbon_records (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL,
    electricity        REAL NOT NULL DEFAULT 0,
    transport_type     TEXT,
    transport_distance REAL NOT NULL DEFAULT 0,
    veg_meals          INTEGER NOT NULL DEFAULT 0,
    nonveg_meals       INTEGER NOT NULL DEFAULT 0,
    electricity_emissions REAL NOT NULL DEFAULT 0,
    transport_emissions   REAL NOT NULL DEFAULT 0,
    food_emissions     REAL NOT NULL DEFAULT 0,
    waste_emissions    REAL NOT NULL DEFAULT 0,
    total_emissions    REAL NOT NULL DEFAULT 0,
    created_at         TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recycling_records (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    material   TEXT NOT NULL,
    quantity   REAL NOT NULL,
    unit       TEXT NOT NULL DEFAULT 'kg',
    method     TEXT,
    notes      TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS zero_waste_goals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    title      TEXT NOT NULL,
    target     REAL NOT NULL,
    current    REAL NOT NULL DEFAULT 0,
    unit       TEXT NOT NULL DEFAULT 'kg',
    deadline   TEXT,
    status     TEXT NOT NULL DEFAULT 'Active',
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS biodiversity_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    species          TEXT NOT NULL,
    category         TEXT NOT NULL,
    location         TEXT,
    observation_date TEXT,
    description      TEXT,
    image_path       TEXT,
    map_x            REAL,
    map_y            REAL,
    created_at       TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS challenges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    duration    TEXT NOT NULL,
    points      INTEGER NOT NULL DEFAULT 50,
    icon        TEXT NOT NULL DEFAULT 'leaf'
);

CREATE TABLE IF NOT EXISTS user_challenges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    challenge_id INTEGER NOT NULL,
    progress     INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'Active',
    joined_at    TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE (user_id, challenge_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (challenge_id) REFERENCES challenges(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommendations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    action      TEXT,
    priority    TEXT NOT NULL DEFAULT 'Medium',
    impact      TEXT,
    difficulty  TEXT DEFAULT 'Easy',
    icon        TEXT DEFAULT 'lightbulb',
    created_at  TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""

DEFAULT_CHALLENGES = [
    ("7-Day Plastic-Free Challenge",
     "Avoid single-use plastic for a full week. Log a day each time you get through it.",
     "7 days", 50, "bottle-water"),
    ("Zero Food Waste Week",
     "Finish what you cook and compost the rest. Track seven days of no food in the bin.",
     "7 days", 50, "utensils"),
    ("Walk Instead of Drive",
     "Replace ten short car trips with walking or cycling.", "14 days", 40, "person-walking"),
    ("Recycle 10 kg Challenge",
     "Send 10 kg of clean, sorted material to recycling.", "30 days", 60, "recycle"),
    ("Plant & Protect Challenge",
     "Plant five saplings and check on them each week.", "30 days", 70, "tree"),
    ("Paper-Free Week",
     "Keep notes, assignments and receipts digital for seven days.", "7 days", 35, "file-lines"),
]


# --------------------------------------------------------------------------- #
# Connection handling
# --------------------------------------------------------------------------- #
def get_db():
    """Return a per-request SQLite connection with dict-like rows."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(sql, args=(), one=False):
    """Run a SELECT. Returns a list of sqlite3.Row (or one row / None)."""
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(sql, args=()):
    """Run an INSERT/UPDATE/DELETE and return the last row id."""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


def row_to_dict(row):
    return dict(row) if row is not None else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


def init_app(app):
    app.teardown_appcontext(close_db)


# --------------------------------------------------------------------------- #
# Schema + demo data
# --------------------------------------------------------------------------- #
def init_db(app):
    """Create tables if missing and make sure the challenge catalogue exists."""
    os.makedirs(os.path.dirname(app.config["DATABASE"]) or ".", exist_ok=True)
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.executescript(SCHEMA)
    for title, desc, duration, points, icon in DEFAULT_CHALLENGES:
        conn.execute(
            "INSERT OR IGNORE INTO challenges (title, description, duration, points, icon) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, desc, duration, points, icon),
        )
    conn.commit()
    conn.close()


def seed_demo_data(app):
    """
    Create the demo account and fill it with believable activity so that the
    dashboard has something to show the moment a reviewer logs in.
    Safe to call repeatedly: it exits early if the demo user already exists.
    """
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    existing = cur.execute(
        "SELECT id FROM users WHERE email = ?", (app.config["DEMO_EMAIL"],)
    ).fetchone()
    if existing:
        conn.close()
        return

    random.seed(11)  # deterministic demo data
    now = datetime.now()

    cur.execute(
        "INSERT INTO users (name, email, password_hash, organization, user_type, "
        "eco_points, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "Demo Student",
            app.config["DEMO_EMAIL"],
            generate_password_hash(app.config["DEMO_PASSWORD"]),
            "Green Valley Institute of Technology",
            "Student",
            1280,
            (now - timedelta(days=210)).isoformat(timespec="seconds"),
        ),
    )
    uid = cur.lastrowid

    # --- Waste records over the last 6 months --------------------------------
    waste_mix = [
        ("Plastic", "PET bottles", 1.2, 4.0),
        ("Paper", "Notebooks and printouts", 0.8, 3.2),
        ("Organic", "Canteen food waste", 1.5, 5.0),
        ("Glass", "Glass jars", 0.4, 1.6),
        ("Metal", "Aluminium cans", 0.3, 1.2),
        ("E-Waste", "Old chargers", 0.2, 0.9),
        ("Textile", "Worn clothing", 0.3, 1.4),
    ]
    for days_ago in range(175, -1, -6):
        category, material, low, high = random.choice(waste_mix)
        cur.execute(
            "INSERT INTO waste_records (user_id, category, material, quantity, unit, "
            "ai_result, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid, category, material, round(random.uniform(low, high), 2), "kg",
                material, round(random.uniform(0.78, 0.96), 2),
                (now - timedelta(days=days_ago)).isoformat(timespec="seconds"),
            ),
        )

    # --- Recycling records ---------------------------------------------------
    methods = ["Municipal collection", "Campus recycling drive", "Scrap dealer", "Compost pit"]
    recycle_mix = [("Plastic", 1.0, 3.5), ("Paper", 1.0, 4.0), ("Glass", 0.5, 2.0),
                   ("Metal", 0.4, 1.8), ("Organic", 1.0, 3.0)]
    for days_ago in range(170, -1, -7):
        material, low, high = random.choice(recycle_mix)
        cur.execute(
            "INSERT INTO recycling_records (user_id, material, quantity, unit, method, "
            "notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                uid, material, round(random.uniform(low, high), 2), "kg",
                random.choice(methods), "Sorted and cleaned before handover.",
                (now - timedelta(days=days_ago)).isoformat(timespec="seconds"),
            ),
        )

    # --- Carbon assessments, one per month, gently improving -----------------
    for months_ago in range(5, -1, -1):
        stamp = now - timedelta(days=30 * months_ago)
        electricity = 210 - (5 - months_ago) * 9 + random.uniform(-8, 8)
        distance = 420 - (5 - months_ago) * 18 + random.uniform(-20, 20)
        elec_e = round(electricity * 0.82, 2)
        trans_e = round(distance * 0.192, 2)
        food_e = round(14 * 0.72 + 7 * 2.10, 2)
        waste_e = round(random.uniform(9, 16), 2)
        cur.execute(
            "INSERT INTO carbon_records (user_id, electricity, transport_type, "
            "transport_distance, veg_meals, nonveg_meals, electricity_emissions, "
            "transport_emissions, food_emissions, waste_emissions, total_emissions, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid, round(electricity, 1), "petrol_car", round(distance, 1), 14, 7,
                elec_e, trans_e, food_e, waste_e,
                round(elec_e + trans_e + food_e + waste_e, 2),
                stamp.isoformat(timespec="seconds"),
            ),
        )

    # --- Zero-waste goals ----------------------------------------------------
    goals = [
        ("Cut plastic waste by 20%", 20, 13, "%", 25, "Active"),
        ("Recycle 50 kg of paper", 50, 50, "kg", -12, "Completed"),
        ("Compost 10 kg of organic waste", 10, 6.5, "kg", 18, "Active"),
        ("Avoid 30 single-use bottles", 30, 22, "bottles", 9, "Active"),
        ("Collect 5 kg of e-waste", 5, 1.5, "kg", -4, "Overdue"),
    ]
    for title, target, current_val, unit, offset, status in goals:
        cur.execute(
            "INSERT INTO zero_waste_goals (user_id, title, target, current, unit, "
            "deadline, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid, title, target, current_val, unit,
                (now + timedelta(days=offset)).date().isoformat(), status,
                (now - timedelta(days=40)).isoformat(timespec="seconds"),
            ),
        )

    # --- Biodiversity observations ------------------------------------------
    observations = [
        ("Indian Peafowl", "Bird", "Campus garden", "Seen near the garden pond at sunrise."),
        ("Common Mormon", "Butterfly", "Botany block", "Feeding on lantana flowers."),
        ("Neem Tree", "Tree", "Main gate avenue", "Mature tree, approximately 8 m tall."),
        ("Tulsi", "Plant", "Hostel courtyard", "Grown in the herb bed by the hostel."),
        ("Rose-ringed Parakeet", "Bird", "Library roof", "Small flock of six birds."),
        ("Garden Lizard", "Small Animal", "Sports ground fence", "Basking on the boundary wall."),
        ("Carpenter Bee", "Insect", "Canteen backyard", "Nesting in an old wooden beam."),
        ("Banyan Tree", "Tree", "Old admin block", "Large canopy, many nesting birds."),
        ("Asian Koel", "Bird", "Staff quarters", "Heard calling through the afternoon."),
        ("Marigold Patch", "Plant", "Entrance lawn", "Planted during the campus greening drive."),
        ("Plain Tiger", "Butterfly", "Herbal garden", "Two individuals on milkweed."),
        ("Indian Robin", "Bird", "Parking area", "Foraging on the ground near the kerb."),
    ]
    for i, (species, category, location, description) in enumerate(observations):
        stamp = now - timedelta(days=i * 5 + 1)
        cur.execute(
            "INSERT INTO biodiversity_records (user_id, species, category, location, "
            "observation_date, description, map_x, map_y, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                uid, species, category, location, stamp.date().isoformat(), description,
                round(random.uniform(8, 92), 1), round(random.uniform(10, 88), 1),
                stamp.isoformat(timespec="seconds"),
            ),
        )

    # --- Challenge participation --------------------------------------------
    challenge_rows = cur.execute("SELECT id FROM challenges ORDER BY id").fetchall()
    states = [(100, "Completed"), (100, "Completed"), (60, "Active"), (35, "Active")]
    for (chal_id,), (progress, status) in zip(
        [(r["id"],) for r in challenge_rows], states
    ):
        joined = now - timedelta(days=random.randint(6, 30))
        cur.execute(
            "INSERT INTO user_challenges (user_id, challenge_id, progress, status, "
            "joined_at, completed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                uid, chal_id, progress, status, joined.isoformat(timespec="seconds"),
                (joined + timedelta(days=7)).isoformat(timespec="seconds")
                if status == "Completed" else None,
            ),
        )

    conn.commit()
    conn.close()
