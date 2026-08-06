"""
Data layer for attendance signups.

Backing store: data/signups.json
Shape: { "<date>": { "<timeslot>": ["name1", "name2", ...] } }

Functions to implement:
- load() -> dict
- save(data: dict) -> None
- add(date: str, timeslot: str, name: str) -> None
- remove(name: str, timeslot: str) -> bool
    Removes `name` from the nearest upcoming date that has `timeslot`.
    Returns True if removed, False if not found.
- get_by_date(date: str) -> dict
    Returns {timeslot: [names]} for that date.
"""

import json
import os
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "signups.json")

def load():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add(date_str, timeslot, name):
    data = load()
    data.setdefault(date_str, {}).setdefault(timeslot, [])
    if name not in data[date_str][timeslot]:
        data[date_str][timeslot].append(name)
    save(data)

def _prune_empty(data, date_str, timeslot):
    if not data.get(date_str, {}).get(timeslot):
        data.get(date_str, {}).pop(timeslot, None)
    if date_str in data and not data[date_str]:
        data.pop(date_str, None)


def remove(name, timeslot):
    data = load()
    today = date.today().isoformat()
    upcoming_dates = sorted(d for d in data if d>= today)
    for d in upcoming_dates:
        names = data.get(d, {}).get(timeslot, [])
        if name in names:
            names.remove(name)
            _prune_empty(data, d, timeslot)
            save(data)
            return d
    return None

def get_by_date(date_str):
    data = load()
    return data.get(date_str, {})

def clear_all():
    save({})

def find_entries(name):
    """Returns a sorted list of (date_str, timeslot) upcoming entries containing `name`."""
    data = load()
    today = date.today().isoformat()
    results = []
    for d in sorted(dd for dd in data if dd >= today):
        for timeslot in sorted(data[d]):
            if name in data[d][timeslot]:
                results.append((d, timeslot))
    return results

def remove_specific(name, date_str, timeslot):
    """Removes `name` from an exact (date_str, timeslot). Returns True if removed."""
    data = load()
    names = data.get(date_str, {}).get(timeslot, [])
    if name in names:
        names.remove(name)
        _prune_empty(data, date_str, timeslot)
        save(data)
        return True
    return False