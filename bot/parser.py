"""
Command parser for /attendance_add and /attendance_remove.

Commands:
- /attendance_add <name> <timeslot>
    Date is NOT typed here — the bot replies with inline buttons
    (today, tomorrow, +2 days, +3 days) and the date is attached
    once the user taps one.
- /attendance_remove <name> <timeslot>

Functions:
- parse_add(text: str) -> dict
    Returns {"name": ..., "timeslot": ...}
- parse_remove(text: str) -> dict
    Returns {"name": ..., "timeslot": ...}
    Both raise ValueError for malformed commands.
- normalize_timeslot(raw: str) -> str
    e.g. "7am", "7.00" -> "0700"
"""

import re

def normalize_timeslot(raw):
    raw = raw.strip().lower().replace(":", "").replace(".", "")

    match = re.match(r"^(\d{1,2})(\d{2})?(am|pm)?$", raw)
    if not match:
        raise ValueError(f"Can't understand timeslot: {raw}")

    hour = int(match.group(1))
    minute = match.group(2) or "00"
    meridiem = match.group(3)
    if meridiem == "pm" and hour != 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0

    return f"{hour:02d}{minute}"

def _parse_args(text, expected_command):
    parts = text.strip().split()
    if not parts:
        raise ValueError("Empty command")

    command = parts[0].split("@")[0]
    if command != expected_command:
        raise ValueError(f"Command must start with {expected_command}")

    if len(parts) < 3:
        raise ValueError(f"Usage: {expected_command} <name> <timeslot>")

    if len(parts) >= 4 and parts[-1].lower() in ("am", "pm"):
        raw_timeslot = parts[-2] + parts[-1]
        name = " ".join(parts[1:-2])
    else:
        raw_timeslot = parts[-1]
        name = " ".join(parts[1:-1])

    return name, normalize_timeslot(raw_timeslot)


def parse_add(text):
    name, timeslot = _parse_args(text, "/attendance_add")
    return {"name": name, "timeslot": timeslot}


def parse_remove(text):
    name, timeslot = _parse_args(text, "/attendance_remove")
    return {"name": name, "timeslot": timeslot}
