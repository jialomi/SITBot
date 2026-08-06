# SITBot — Canoe Sprint Attendance Bot

Telegram bot that automates attendance list-taking for SIT Canoe Sprint training sessions.

## Commands

- `/attendance add <name> <date> <timeslot>` — add a name to a training slot
- `/attendance remove <name> <timeslot>` — remove a name from the nearest upcoming date with that timeslot

Every add/remove posts a fresh, fully updated list to the chat.

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and fill in your bot token from @BotFather.
3. Run the bot:
   ```
   python -m bot.main
   ```

## Project structure

- `bot/storage.py` — JSON-backed data layer (`data/signups.json`)
- `bot/parser.py` — command parsing and date/timeslot normalization
- `bot/renderer.py` — formats signup data into the chat's list text format
- `bot/main.py` — bot runtime, wires everything together

## Status

Skeleton only — see TODOs in each module.
