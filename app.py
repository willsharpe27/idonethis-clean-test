from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import datetime
import random
from collections import defaultdict
import os

app = Flask(__name__)
app.secret_key = "your-secret-key"
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "entries.db")

def init_db():
    print(f"\U0001F4CD Current working directory: {os.getcwd()}")
    print(f"\U0001F6A3️ Absolute DB path: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("🆕 Creating new database and table...")
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_on DATE NOT NULL,
                    body TEXT NOT NULL
                )
            """)
        print("✅ entries.db created successfully.")
    else:
        print("✅ Database found at", DB_PATH)

def query_db(query, args=(), one=False):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(query, args)
        conn.commit()

@app.route("/", methods=["GET", "POST"])
def today_entries():
    today = datetime.datetime.now()

    if request.method == "POST":
        body = request.form.get("body").strip()
        date_input = request.form.get("occurred_on")
        try:
            occurred_on = datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
            if body:
                execute_db(
                    "INSERT INTO entries (occurred_on, body) VALUES (?, ?)",
                    (occurred_on, body)
                )
                flash(f"Reflection added for {occurred_on.strftime('%B %d, %Y')}!", "success")
                return redirect(url_for("today_entries"))
        except ValueError:
            flash("Invalid date format.", "danger")

    month_day = today.strftime("%m-%d")
    matches = query_db(
        "SELECT * FROM entries WHERE strftime('%m-%d', occurred_on) = ?",
        (month_day,)
    )

    selected = []
    if matches:
        random_year = random.choice(list(set([entry['occurred_on'][:4] for entry in matches])))
        selected = [entry for entry in matches if entry['occurred_on'].startswith(random_year)]

    # New: Fast check within 14 days window for under-logged dates
    fourteen_days_ago = today.date() - datetime.timedelta(days=14)
    result = query_db(
        "SELECT occurred_on, COUNT(*) as cnt FROM entries WHERE occurred_on BETWEEN ? AND ? GROUP BY occurred_on HAVING cnt < 3 ORDER BY occurred_on ASC LIMIT 1",
        (str(fourteen_days_ago), str(today.date())),
        one=True
    )
    print(f"🕵️ Suggested check: {result}")

    if result and datetime.datetime.strptime(result["occurred_on"], "%Y-%m-%d").date() >= fourteen_days_ago:
        suggested_date = datetime.datetime.strptime(result["occurred_on"], "%Y-%m-%d").date()
        entry_count = result["cnt"]
    else:
        suggested_date = today.date()
        entry_count = 0

    suggested_label = f"🎯 Write your reflection for {suggested_date.strftime('%A (%B %d, %Y)')}..."

    return render_template(
        "today.html",
        entries=selected,
        today=today.strftime("%B %d"),
        suggested_date=suggested_date.strftime("%Y-%m-%d"),
        suggested_label=suggested_label,
        reflection_progress=entry_count
    )

@app.route("/history")
def history():
    search = request.args.get("q", "").strip().lower()
    if search:
        entries = query_db(
            "SELECT * FROM entries WHERE LOWER(body) LIKE ? ORDER BY occurred_on DESC",
            (f"%{search}%",)
        )
    else:
        entries = query_db("SELECT * FROM entries ORDER BY occurred_on DESC")

    grouped = defaultdict(list)
    for row in entries:
        year = row['occurred_on'][:4]
        grouped[year].append(row)

    grouped = dict(sorted(grouped.items(), reverse=True))
    return render_template("history.html", entries_by_year=grouped, search=search)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        body = request.form.get("body").strip()
        date_input = request.form.get("occurred_on")
        try:
            occurred_on = datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
            if body:
                execute_db(
                    "INSERT INTO entries (occurred_on, body) VALUES (?, ?)",
                    (occurred_on, body)
                )
                return redirect(url_for("today_entries"))
        except ValueError:
            pass
    return render_template("add.html")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"🔌 Starting on port: {port}")
    app.run(host="0.0.0.0", port=port)
