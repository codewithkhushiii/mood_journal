from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from datetime import date
from collections import Counter

app = Flask(__name__)

DATA_FILE = "mood_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    data = load_data()
    return render_template("index.html", entries=data[-10:])  # ✔️ This links index.html

@app.route('/add', methods=['POST'])
def add_entry():
    mood = request.form.get("mood")
    note = request.form.get("note", "")
    today = date.today().isoformat()

    data = load_data()
    data.append({"date": today, "mood": mood, "note": note})
    save_data(data)
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    data = load_data()
    if not data:
        return jsonify({"message": "No data for statistics."})
    moods = [entry["mood"] for entry in data]
    counter = Counter(moods)
    most_common = counter.most_common(1)[0]
    return jsonify({
        "total_entries": len(data),
        "most_frequent_mood": most_common[0],
        "count": most_common[1]
    })

if __name__ == "__main__":
    app.run(debug=True)
