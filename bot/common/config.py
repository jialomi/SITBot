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

INFO_TEXT = """📋 <b>Attendance System</b>

Every day at 8am, the bot posts the next day's attendance list in the Attendance List topic. Tap <b>Coming</b> to add yourself, <b>Remove Me</b> to take yourself off, or <b>Crew</b> if you're signing up as a K2/K4 pair (e.g. jer/glenn or jer/jw/gab/jos).

<b>Cut-off</b>
All attendance to be sent in by <b>8pm</b> every day, before forwarding to coach, so he knows who's down beforehand.

If sent after 8pm, send it in the group chat with coach instead. Indicate your reason for submitting attendance late when you update it — this includes last-minute additions when your schedule suddenly clears up.

This is for accountability, as all of us are using school equipment."""

ADD_NAME, ADD_TIMESLOT = range(2)
CREW_NAME, CREW_TIMESLOT = range(2)
REMOVE_NAME = 0
COMING_TIMESLOT = 0
REMOVE_OTHER_NAME = 0