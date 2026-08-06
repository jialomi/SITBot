# SITBot — Canoe Sprint Attendance Bot

Telegram bot that automates attendance list-taking for SIT Canoe Sprint training sessions. Self-hosted, long-polling, Python (`python-telegram-bot` 21.6). Built around two topics in the same group chat: **Attendance INFO** (how the system works, plus quick sign-up buttons) and **Attendance List** (the live, auto-updated attendance list).

## Features

- **Attendance INFO topic** — a pinned-style message explaining the system, with two buttons:
  - **Add Attendance** — adds you (using your Telegram first name) after asking for a timeslot and date.
  - **Remove Attendance** — removes you immediately if you're on one slot, or shows a picker if you're on several.
- **Attendance List topic** — one message per date, kept updated in place: the first signup for a date posts a new message (with a **Coming** button attached so anyone can add themselves to that date directly — past dates are rejected), and every add/remove after that edits the same message rather than posting a new one. If a date's list empties out, the message is deleted; the next signup for that date starts fresh.
- Success confirmations ("✅ Successfully added/removed") auto-delete after 10 seconds so the chat doesn't fill up with noise.

### User commands

- `/attendance_add` / `/attendance_remove` — usable by anyone to add/remove *any* name, not just their own. Supports a one-liner (`/attendance_add John Tan 7pm`) or a step-by-step flow (just `/attendance_add`, then answer the prompts). `/cancel` bails out of a step-by-step flow at any point. Both the command and its prompts stay in whichever topic you typed in, and clean up after themselves once done.

### Admin commands

- `/assign` — walks through assigning a boat to every signed-up name for a chosen date.
- `/clearassign <ddmmyy>` — clears all boat assignments for one date (e.g. `/clearassign 060826` for 6 Aug 2026).
- `/attendance_clear` — wipes all signups, boat assignments, and tracked list messages.
- `/whereami` — replies with the current chat ID and topic (thread) ID; useful for finding IDs when adding new topics. Not permission-gated, but only really needed for setup/admin work.

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in:
   - `TELEGRAM_BOT_TOKEN` — from @BotFather
   - `ADMIN_USER_IDS` — comma-separated Telegram user IDs allowed to run admin commands
   - `ATTENDANCE_CHAT_ID` — the group's chat ID (shared by both topics)
   - `ATTENDANCE_INFO_THREAD_ID` / `ATTENDANCE_LIST_THREAD_ID` — the `message_thread_id` of each topic (use `/whereami` inside each topic to find these)
3. Make sure the bot is a group admin with **Delete Messages** permission — several features (message cleanup, `/attendance_clear`) rely on it.
4. Run the bot:
   ```
   python -m bot.main
   ```
   On startup, the console logs each handler file as it's auto-loaded.

## Project structure

```
bot/
  common.py            — shared constants, env config, and helper functions
  storage.py           — JSON-backed signups (data/signups.json)
  boatstore.py          — JSON-backed boat assignments (data/assignments.json)
  liststore.py           — tracks which message ID holds each date's posted list (data/list_messages.json), so it can be edited in place
  parser.py             — command parsing and timeslot normalization
  renderer.py            — formats the posted attendance list
  main.py                — entrypoint: builds the bot and auto-registers handlers
  handlers/
    commands/            — one file per CommandHandler (e.g. /assign, /whereami)
    callbacks/            — one file per CallbackQueryHandler (button taps)
    messages/             — one file per MessageHandler (e.g. !info trigger)
    others/               — ConversationHandlers (multi-step flows like /attendance_add)
```

Handlers are auto-discovered: `main.py` scans each `handlers/` subfolder and registers every file that defines a module-level `handler` variable. Adding a new command/callback/message just means dropping a new file in the right folder — no changes to `main.py` needed.

## Status

Actively used and maintained. See `PROJECT_STATUS.md` for session handoff notes (not tracked in git).
