import os
import asyncio
from datetime import date, timedelta, datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CommandHandler
from telegram.error import BadRequest

from bot import parser, storage, renderer, boatstore, liststore

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
INFO_ADD_TIMESLOT = 0
REMOVE_NAME = 0
COMING_TIMESLOT = 0


async def _delete_after(msg, seconds):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass


async def _delete_message(context, chat_id, message_id):
    if message_id is None:
        return
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def _command_has_args(text):
    """True if there's anything after the command word itself."""
    return len(text.strip().split()) > 1


async def _send_date_picker(context, chat_id, name, timeslot, thread_id=None):
    buttons = []
    for offset in range(4):
        d = date.today() + timedelta(days=offset)
        d_iso = d.isoformat()
        label = renderer.format_date_label(d_iso)
        callback_data = f"add|{name}|{timeslot}|{d_iso}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])

    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text="Pick a date:", reply_markup=keyboard)


async def _post_updated_list(context, date_str):
    """Posts the rendered list for a date, with a 'Coming' button, or nothing if it's empty."""
    liststore.cleanup_old()
    slots = storage.get_by_date(date_str)
    message_id = liststore.get_message_id(date_str)

    if not slots:
        if message_id:
            await _delete_message(context, int(ATTENDANCE_CHAT_ID), message_id)
            liststore.clear_message_id(date_str)
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Coming", callback_data=f"coming|{date_str}")]]
    )
    text = renderer.render(date_str, slots)

    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=int(ATTENDANCE_CHAT_ID), message_id=message_id,
                text=text, reply_markup=keyboard,
            )
            return
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                return
            liststore.clear_message_id(date_str)

    msg = await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID), message_thread_id=int(ATTENDANCE_LIST_THREAD_ID),
        text=text, reply_markup=keyboard,
    )
    liststore.set_message_id(date_str, msg.message_id)


async def _do_remove(context, chat_id, name, timeslot):
    removed_date = storage.remove(name, timeslot)
    if not removed_date:
        msg = await context.bot.send_message(
            chat_id=chat_id, text=f"{name} wasn't found on timeslot {timeslot}."
        )
        asyncio.create_task(_delete_after(msg, 10))
        return
    boatstore.remove_assignment(removed_date, timeslot, name)
    await _post_updated_list(context, removed_date)


async def cancel(update, context):
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    context.user_data.clear()
    await _delete_message(context, update.effective_chat.id, prev_prompt_id)
    await _delete_message(context, update.effective_chat.id, update.message.message_id)
    msg = await update.message.reply_text("Cancelled.")
    asyncio.create_task(_delete_after(msg, 3))
    return ConversationHandler.END


async def _prompt_next_boat(context, chat_id):
    """Reads assign_* progress out of chat_data and either prompts for the
    next name's boat, advances to the next timeslot, or wraps up and posts
    the final assigned list."""
    date_str = context.chat_data["assign_date"]
    timeslots = context.chat_data["assign_timeslots"]
    ts_index = context.chat_data["assign_ts_index"]

    if ts_index >= len(timeslots):
        assignments = boatstore.get_all_assigned_for_date(date_str)
        slots = storage.get_by_date(date_str)
        text = renderer.render_assigned(date_str, slots, assignments)
        for key in (
            "assign_date", "assign_timeslots", "assign_ts_index",
            "assign_timeslot", "assign_names", "assign_name_index",
            "assign_prompt_msg_id",
        ):
            context.chat_data.pop(key, None)
        await context.bot.send_message(chat_id=chat_id, text=text)
        return

    timeslot = timeslots[ts_index]
    names = context.chat_data.get("assign_names")
    if names is None:
        names = storage.get_by_date(date_str).get(timeslot, [])
        context.chat_data["assign_timeslot"] = timeslot
        context.chat_data["assign_names"] = names
        context.chat_data["assign_name_index"] = 0

    name_index = context.chat_data["assign_name_index"]

    if name_index >= len(names):
        context.chat_data["assign_ts_index"] = ts_index + 1
        context.chat_data.pop("assign_timeslot", None)
        context.chat_data.pop("assign_names", None)
        context.chat_data.pop("assign_name_index", None)
        await _prompt_next_boat(context, chat_id)
        return

    name = names[name_index]
    available = boatstore.get_available_boats(date_str, timeslot)
    if not available:
        msg = await context.bot.send_message(
            chat_id=chat_id, text=f"No boats left to assign {name} ({timeslot}). Skipping."
        )
        asyncio.create_task(_delete_after(msg, 5))
        context.chat_data["assign_name_index"] = name_index + 1
        await _prompt_next_boat(context, chat_id)
        return

    buttons = [[InlineKeyboardButton(b, callback_data=f"assignboat|{b}")] for b in available]
    prompt = await context.bot.send_message(
        chat_id=chat_id,
        text=f"{timeslot} — pick a boat for {name}:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    context.chat_data["assign_prompt_msg_id"] = prompt.message_id