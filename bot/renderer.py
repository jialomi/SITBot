"""
Renders signup data for a date into the group's list format:

4 Aug (Tue)

0700

1. Jeremy
2. XXXX

0800

1. XXXX

Functions to implement:
- render(date: str, slots: dict) -> str
    slots is {timeslot: [names]}, as returned by storage.get_by_date
"""

from datetime import date

def format_date_label(date_str):
    d = date.fromisoformat(date_str)
    return f"{d.day} {d.strftime('%b')} ({d.strftime('%a')})"

def render(date_str, slots):
    lines = [format_date_label(date_str), ""]

    for timeslot in sorted(slots):
        names = slots[timeslot]
        if not names:
            continue
        lines.append(timeslot)
        for i, name in enumerate(names, start=1):
            lines.append(f"{i}. {name}")
        lines.append("")

    return "\n".join(lines).strip()

def render_assigned(date_str, slots, assignments):
    """Same as render(), but appends '- boat' next to each name that has one.

    assignments is {timeslot: {name: boat}}, as returned by
    boatstore.get_all_assigned_for_date.
    """
    lines = [format_date_label(date_str), ""]

    for timeslot in sorted(slots):
        names = slots[timeslot]
        if not names:
            continue
        lines.append(timeslot)
        ts_assignments = assignments.get(timeslot, {})
        for i, name in enumerate(names, start=1):
            boat = ts_assignments.get(name)
            if boat:
                lines.append(f"{i}. {name} - {boat}")
            else:
                lines.append(f"{i}. {name}")
        lines.append("")

    return "\n".join(lines).strip()