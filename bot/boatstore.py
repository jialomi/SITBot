"""
Boat assignment layer.

boatList.json (data/boatList.json): the master pool of boats, grouped by
category. For now /assign shows them as one flat list (not grouped) so we
can see whether that's too cluttered as buttons.
Shape: { "<category>": ["boat1", "boat2", ...] }

assignments.json (data/assignments.json): which boat each person got, per
date + timeslot. Shape: { "<date>": { "<timeslot>": { "<name>": "<boat>" } } }
"""

import json
import os

BOATLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "boatList.json")
ASSIGN_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "assignments.json")


def load_boat_list():
    if not os.path.exists(BOATLIST_FILE):
        return {}
    with open(BOATLIST_FILE, "r") as f:
        return json.load(f)


def flatten_boats():
    """All boats across every category, in file order."""
    boats = []
    for category_boats in load_boat_list().values():
        boats.extend(category_boats)
    return boats


def load_assignments():
    if not os.path.exists(ASSIGN_FILE):
        return {}
    with open(ASSIGN_FILE, "r") as f:
        return json.load(f)


def save_assignments(data):
    with open(ASSIGN_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_assigned(date_str, timeslot):
    """{name: boat} already assigned for this date+timeslot."""
    data = load_assignments()
    return data.get(date_str, {}).get(timeslot, {})


def get_all_assigned_for_date(date_str):
    """{timeslot: {name: boat}} for the whole date."""
    data = load_assignments()
    return data.get(date_str, {})


def get_available_boats(date_str, timeslot):
    """Every boat not already assigned to someone in this date+timeslot."""
    taken = set(get_assigned(date_str, timeslot).values())
    return [b for b in flatten_boats() if b not in taken]


def assign_boat(date_str, timeslot, name, boat):
    data = load_assignments()
    data.setdefault(date_str, {}).setdefault(timeslot, {})[name] = boat
    save_assignments(data)


def remove_assignment(date_str, timeslot, name):
    """Frees up the boat if `name` had one assigned here. No-op otherwise."""
    data = load_assignments()
    ts = data.get(date_str, {}).get(timeslot, {})
    if name in ts:
        ts.pop(name)
        if not ts:
            data.get(date_str, {}).pop(timeslot, None)
        if date_str in data and not data[date_str]:
            data.pop(date_str, None)
        save_assignments(data)

def clear_date(date_str):
    """Clears all boat assignments for one date. No-op if none exist."""
    data = load_assignments()
    if date_str in data:
        data.pop(date_str)
        save_assignments(data)

def clear_all():
    save_assignments({})
