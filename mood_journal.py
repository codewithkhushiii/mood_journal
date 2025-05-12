import json
import os
from datetime import date, datetime
from collections import Counter

DATA_FILE = "mood_data.json"

# Load existing data
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

# Save data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Add new entry
def add_entry():
    today = date.today().isoformat()
    mood = input("Enter your mood (Happy, Sad, Neutral, etc.): ")
    note = input("Add a short note (optional): ")
    data = load_data()
    data.append({"date": today, "mood": mood, "note": note})
    save_data(data)
    print("Entry saved.")

# View all entries
def view_entries():
    data = load_data()
    if not data:
        print("No entries found.")
        return
    for entry in data[-10:]:  # Show last 10 entries
        print(f"{entry['date']} - {entry['mood']}: {entry['note']}")

# View statistics
def view_stats():
    data = load_data()
    if not data:
        print("No data for statistics.")
        return
    moods = [entry["mood"] for entry in data]
    counter = Counter(moods)
    most_common = counter.most_common(1)[0]
    print(f"Total entries: {len(data)}")
    print(f"Most frequent mood: {most_common[0]} ({most_common[1]} times)")

# Menu
def main():
    while True:
        print("\n--- Personal Mood Journal ---")
        print("1. Add new mood entry")
        print("2. View recent entries")
        print("3. View mood statistics")
        print("4. Exit")
        choice = input("Choose an option: ")

        if choice == "1":
            add_entry()
        elif choice == "2":
            view_entries()
        elif choice == "3":
            view_stats()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()