import os

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("ADMIN_USER_IDS", "").split(",")
    if uid.strip()
}
ATTENDANCE_CHAT_ID = os.getenv("ATTENDANCE_CHAT_ID")
ATTENDANCE_INFO_THREAD_ID = os.getenv("ATTENDANCE_INFO_THREAD_ID")
ATTENDANCE_LIST_THREAD_ID = os.getenv("ATTENDANCE_LIST_THREAD_ID")

INFO_TEXT = """📋 <b>Attendance System — How It Works</b>

Use this to sign yourself up for training slots, or manage attendance for others.

<b>Quick sign-up (buttons below)</b>
- Tap <b>Add Attendance</b> — you'll be asked which date and timeslot, then you're added.
- Tap <b>Remove Attendance</b> — if you're only signed up for one slot, you're removed right away. If you're on multiple, you'll get a list to pick from.

<b>Commands (for adding/removing anyone, not just yourself)</b>
- <code>/attendance_add</code> — walks you through adding a name, or type it all in one line: <code>/attendance_add John Tan 7pm</code>
- <code>/attendance_remove</code> — same idea, for removing someone: <code>/attendance_remove John Tan 7pm</code>

<b>Cut-off</b>
Try to have your attendance in by <b>8PM the night before</b> — it helps with planning. Last-minute changes are still fine, so don't stress if something comes up late.

The attendance list itself is posted and kept updated in the Attendance List topic."""

ADD_NAME, ADD_TIMESLOT = range(2)
CREW_NAME, CREW_TIMESLOT = range(2)
INFO_ADD_TIMESLOT = 0
REMOVE_NAME = 0
COMING_TIMESLOT = 0
