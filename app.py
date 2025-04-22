from flask import Flask, render_template, request, redirect, url_for, flash
import datetime
import random
from collections import defaultdict
import os
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Supabase config
SUPABASE_URL = "https://ofqnvdpvzwbjervsslce.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mcW52ZHB2endiamVydnNzbGNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQxNTM0MzAsImV4cCI6MjA1OTcyOTQzMH0.Hub7LvdM4H7smquqJKo2LeLGA8PIAQDiv8_tuxvAuQQ"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def query_entries(query_date):
    result = supabase.table("entries").select("*").eq("occurred_on", query_date).execute()
    return result.data if result.data else []

def insert_entry(date, body):
    supabase.table("entries").insert({"occurred_on": date, "body": body}).execute()

def count_entries_for_date(date):
    result = supabase.table("entries").select("id", count="exact").eq("occurred_on", date).execute()
    return result.count if result.count else 0

def get_all_entries():
    result = supabase.table("entries").select("*").order("occurred_on", desc=True).limit(1000).execute()
    return result.data if result.data else []

def parse_occurred_on(entry_date):
    if isinstance(entry_date, str):
        return datetime.datetime.strptime(entry_date, "%Y-%m-%d").date()
    elif isinstance(entry_date, dict) and {"year", "month", "day"}.issubset(entry_date):
        return datetime.date(entry_date["year"], entry_date["month"], entry_date["day"])
    elif isinstance(entry_date, datetime.date):
        return entry_date
    raise ValueError(f"Unknown date format: {entry_date}")

def get_matches_for_month_day(month_day):
    result = supabase.table("entries").select("*").limit(1000).execute()

    print("✅ ALL ENTRIES FROM SUPABASE:")
    print("🔍 Raw Supabase result:", result)
    print("🔢 Result count:", len(result.data) if result.data else 0)

    matches = []
    for entry in result.data:
        try:
            print("🔍 Raw entry:", entry)
            entry_date = parse_occurred_on(entry["occurred_on"])
            print("🔍 Parsed date:", entry_date, "| Formatted:", entry_date.strftime("%m-%d"))
            if entry_date.strftime("%m-%d") == month_day:
                matches.append(entry)
        except Exception as e:
            print("❌ Error parsing entry:", entry, "| Error:", e)

    print(f"✅ MATCHES for {month_day}: {len(matches)} found")
    return matches

@app.route("/", methods=["GET", "POST"])
def today_entries():
    print("🟢 TODAY ENTRIES ROUTE HIT")
    today = datetime.datetime.now().date()

    if request.method == "POST":
        body = request.form.get("body").strip()
        date_input = request.form.get("occurred_on")
        try:
            occurred_on = datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
            if body:
                insert_entry(str(occurred_on), body)
                flash(f"Reflection added for {occurred_on.strftime('%B %d, %Y')}!", "success")
                return redirect(url_for("today_entries"))
        except ValueError:
            flash("Invalid date format.", "danger")

    month_day = today.strftime("%m-%d")
    print("▶️ Checking against month_day:", month_day)
    matches = get_matches_for_month_day(month_day)

    selected = []
    if matches:
        random_year = random.choice(list(set([str(parse_occurred_on(entry['occurred_on']).year) for entry in matches])))
        selected = [entry for entry in matches if str(parse_occurred_on(entry['occurred_on']).year) == random_year][:3]

    fourteen_days_ago = today - datetime.timedelta(days=14)
    recent_dates = [fourteen_days_ago + datetime.timedelta(days=i) for i in range(15)]

    suggested_date = today
    entry_count = 0
    for date in recent_dates:
        count = count_entries_for_date(str(date))
        if count < 3:
            suggested_date = date
            entry_count = count
            break

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
    entries = get_all_entries()
    if search:
        entries = [entry for entry in entries if search in entry['body'].lower()]

    grouped = defaultdict(list)
    for row in entries:
        year = str(parse_occurred_on(row['occurred_on']).year)
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
                insert_entry(str(occurred_on), body)
                return redirect(url_for("today_entries"))
        except ValueError:
            pass
    return render_template("add.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🔌 Starting on port: {port}")
    app.run(host="0.0.0.0", port=port)
