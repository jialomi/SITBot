"""
Tracks which message ID holds the posted attendance list for each date, so
the list can be edited in place instead of reposted every time someone is
added or removed.

Backing store: data/list_messages.json
Shape: { "<date>": <message_id> }
"""
import json
import os
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "list_messages.json")

def load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_message_id(date_str):
    return load().get(date_str)

def set_message_id(date_str, message_id):
    data = load()
    data[date_str] = message_id
    save(data)

def clear_message_id(date_str):
    data = load()
    if date_str in data:
        data.pop(date_str)
        save(data)

def clear_all():
    save({})

def cleanup_old():
    """Removes tracking entries for dates that have already passed."""
    data = load()
    today = date.today().isoformat()
    remaining = {d: mid for d, mid in data.items() if d >= today}
    if remaining != data:
        save(remaining)