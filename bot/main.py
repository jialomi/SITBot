"""
Entrypoint. Long-polling bot runtime.

/attendance_add and /attendance_remove each support two ways of being used:
- One-liner: /attendance_add <name> <timeslot> (or /attendance_remove ...)
  -> parsed immediately, same as before.
- Step-by-step: /attendance_add with no extra text
  -> bot asks for the name, then asks for the timeslot, one message at a time.
  /cancel bails out of an in-progress step-by-step flow.

TODO:
- Load TELEGRAM_BOT_TOKEN from .env
- Register command handler for /attendance
- Start polling
"""

import os
import asyncio
from datetime import date, timedelta, datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot import parser, storage, renderer, boatstore

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

# Attendance INFO Text
INFO_TEXT = """📋 <b>Attendance System — How It Works</b>

Use this to sign yourself up for training slots, or manage attendance for others.

<b>Quick sign-up (buttons below)</b>
• Tap <b>Add Attendance</b> — you'll be asked which date and timeslot, then you're added.
• Tap <b>Remove Attendance</b> — if you're only signed up for one slot, you're removed right away. If you're on multiple, you'll get a list to pick from.

<b>Commands (for adding/removing anyone, not just yourself)</b>
• <code>/attendance_add</code> — walks you through adding a name, or type it all in one line: <code>/attendance_add John Tan 7pm</code>
• <code>/attendance_remove</code> — same idea, for removing someone: <code>/attendance_remove John Tan 7pm</code>

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
    slots = storage.get_by_date(date_str)
    if not slots:
        return
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Coming", callback_data=f"coming|{date_str}")]]
    )
    await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID), message_thread_id=int(ATTENDANCE_LIST_THREAD_ID), text=renderer.render(date_str, slots), reply_markup=keyboard
    )


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

async def info_add_entry(update, context):
    query = update.callback_query
    await query.answer()
    name = query.from_user.first_name
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    prompt = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text=f"What timeslot would you like, {name}?"
    )
    context.user_data["info_add_name"] = name
    context.user_data["info_add_thread_id"] = thread_id
    context.user_data["prompt_msg_id"] = prompt.message_id
    return INFO_ADD_TIMESLOT

async def info_add_receive_timeslot(update, context):
    raw = update.message.text.strip()
    try:
        timeslot = parser.normalize_timeslot(raw)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return INFO_ADD_TIMESLOT

    chat_id = update.effective_chat.id
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)

    name = context.user_data.pop("info_add_name", None)
    thread_id = context.user_data.pop("info_add_thread_id", None)
    await _send_date_picker(context, chat_id, name, timeslot, thread_id=thread_id)
    return ConversationHandler.END


# ---- !info ----
async def info_trigger(update, context):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Add Attendance", callback_data="info_add"),
            InlineKeyboardButton("Remove Attendance", callback_data="info_remove"),
        ]
    ])
    await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID),
        message_thread_id=int(ATTENDANCE_INFO_THREAD_ID),
        text=INFO_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard,
    )

# ---- /attendance_add ----

async def add_entry(update, context):
    text = update.message.text
    if not _command_has_args(text):
        prompt = await update.message.reply_text("Who's this for? Type a name.")
        context.user_data["prompt_msg_id"] = prompt.message_id
        return ADD_NAME

    try:
        parsed = parser.parse_add(text)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    await _send_date_picker(context, update.effective_chat.id, parsed["name"], parsed["timeslot"])
    return ConversationHandler.END


async def add_receive_name(update, context):
    context.user_data["add_name"] = update.message.text.strip()
    context.user_data["add_name_msg_id"] = update.message.message_id

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, update.effective_chat.id, prev_prompt_id)

    prompt = await update.message.reply_text("What timeslot? (e.g. 0700, 7pm)")
    context.user_data["prompt_msg_id"] = prompt.message_id
    return ADD_TIMESLOT


async def add_receive_timeslot(update, context):
    raw = update.message.text.strip()
    try:
        timeslot = parser.normalize_timeslot(raw)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return ADD_TIMESLOT

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, update.effective_chat.id, prev_prompt_id)

    name_msg_id = context.user_data.pop("add_name_msg_id", None)
    await _delete_message(context, update.effective_chat.id, name_msg_id)
    await _delete_message(context, update.effective_chat.id, update.message.message_id)

    name = context.user_data.pop("add_name", None)
    await _send_date_picker(context, update.effective_chat.id, name, timeslot)
    return ConversationHandler.END


# ---- /attendance_remove ----

async def remove_entry(update, context):
    text = update.message.text
    if not _command_has_args(text):
        prompt = await update.message.reply_text("Who do you want to remove? Type a name.")
        context.user_data["prompt_msg_id"] = prompt.message_id
        return REMOVE_NAME

    try:
        parsed = parser.parse_remove(text)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    await _do_remove(context, update.effective_chat.id, parsed["name"], parsed["timeslot"])
    return ConversationHandler.END


async def remove_receive_name(update, context):
    name = update.message.text.strip()
    chat_id = update.effective_chat.id

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    context.user_data.clear()
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)

    entries = storage.find_entries(name)

    if not entries:
        msg = await context.bot.send_message(
            chat_id=chat_id, text=f"{name} wasn't found on any upcoming slot."
        )
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    if len(entries) == 1:
        date_str, timeslot = entries[0]
        storage.remove_specific(name, date_str, timeslot)
        boatstore.remove_assignment(date_str, timeslot, name)
        await _post_updated_list(context, date_str)
        return ConversationHandler.END

    buttons = []
    for date_str, timeslot in entries:
        label = f"{renderer.format_date_label(date_str)} {timeslot}"
        callback_data = f"remove|{name}|{date_str}|{timeslot}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])
    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id, text="Which one do you want to remove?", reply_markup=keyboard
    )
    return ConversationHandler.END

async def info_remove_entry(update, context):
    query = update.callback_query
    await query.answer()

    name = query.from_user.first_name
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    entries = storage.find_entries(name)

    if not entries:
        msg = await context.bot.send_message(
            chat_id = chat_id, message_thread_id=thread_id,
            text = f"{name} wasn't found on any upcoming slots"
        )
        asyncio.create_task(_delete_after(msg, 10))
        return

    if len(entries) == 1:
        date_str, timeslot = entries[0]
        storage.remove_specific(name, date_str, timeslot)
        boatstore.remove_assignment(date_str, timeslot, name)
        await _post_updated_list(context, date_str)

        confirm = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id, text="✅ Successfully removed."
        )
        asyncio.create_task(_delete_after(confirm, 10))
        return

    buttons = []
    for date_str, timeslot in entries:
        label = f"{renderer.format_date_label(date_str)} {timeslot}"
        callback_data = f"remove|{name}|{date_str}|{timeslot}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])
    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text="Which one do you want to remove?", reply_markup=keyboard
    )


# ---- "Coming" button ----

async def coming_entry(update, context):
    query = update.callback_query

    _, date_str = query.data.split("|")

    if date.fromisoformat(date_str) < date.today():
        await query.answer("This date has already passed.", show_alert=True)
        return ConversationHandler.END

    await query.answer()

    name = query.from_user.first_name
    chat_id = query.message.chat_id

    prompt = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=int(ATTENDANCE_LIST_THREAD_ID), text=f"What time would you like to go down, {name}?"
    )
    context.user_data["coming_name"] = name
    context.user_data["coming_date"] = date_str
    context.user_data["prompt_msg_id"] = prompt.message_id
    return COMING_TIMESLOT


async def coming_receive_timeslot(update, context):
    raw = update.message.text.strip()
    try:
        timeslot = parser.normalize_timeslot(raw)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return COMING_TIMESLOT

    chat_id = update.effective_chat.id
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)

    name = context.user_data.pop("coming_name", None)
    date_str = context.user_data.pop("coming_date", None)
    storage.add(date_str, timeslot, name)
    await _post_updated_list(context, date_str)

    confirm = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=int(ATTENDANCE_LIST_THREAD_ID), text="✅ Successfully added."
    )
    asyncio.create_task(_delete_after(confirm, 10))
    return ConversationHandler.END


async def cancel(update, context):
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    context.user_data.clear()
    await _delete_message(context, update.effective_chat.id, prev_prompt_id)
    msg = await update.message.reply_text("Cancelled.")
    asyncio.create_task(_delete_after(msg, 3))
    return ConversationHandler.END


async def whereami(update, context):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    await update.message.reply_text(f"chat_id: {chat_id}\nmessage_thread_id: {thread_id}")


async def clear_command(update, context):
    if update.effective_user.id not in ADMIN_USER_IDS:
        msg = await update.message.reply_text("You don't have permission to do that.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    storage.clear_all()
    boatstore.clear_all()
    msg = await update.message.reply_text("All signups cleared.")
    asyncio.create_task(_delete_after(msg, 3))
    try:
        await update.message.delete()
    except Exception:
        pass


async def handle_date_choice(update, context):
    query = update.callback_query
    await query.answer()

    _, name, timeslot, date_str = query.data.split("|")
    storage.add(date_str, timeslot, name)

    await _post_updated_list(context, date_str)
    await _delete_message(context, query.message.chat_id, query.message.message_id)

    confirm = await context.bot.send_message(
        chat_id = query.message.chat_id,
        message_thread_id=query.message.message_thread_id,
        text="✅ Successfully added."
    )
    asyncio.create_task(_delete_after(confirm, 10))


async def handle_remove_choice(update, context):
    query = update.callback_query
    await query.answer()

    _, name, date_str, timeslot = query.data.split("|")
    storage.remove_specific(name, date_str, timeslot)
    boatstore.remove_assignment(date_str, timeslot, name)

    await _post_updated_list(context, date_str)
    await _delete_message(context, query.message.chat_id, query.message.message_id)

    confirm = await context.bot.send_message(
        chat_id=query.message.chat_id,
        message_thread_id=query.message.message_thread_id,
        text="✅ Successfully removed."
    )


# ---- /assign ----

async def assign_command(update, context):
    if update.effective_user.id not in ADMIN_USER_IDS:
        msg = await update.message.reply_text("You don't have permission to do that.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    data = storage.load()
    dates = sorted(d for d in data if data[d])
    if not dates:
        msg = await update.message.reply_text("No signups to assign boats for yet.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    buttons = [
        [InlineKeyboardButton(renderer.format_date_label(d), callback_data=f"assigndate|{d}")]
        for d in dates
    ]
    await update.message.reply_text(
        "Assign boats for which date?", reply_markup=InlineKeyboardMarkup(buttons)
    )

# ---- /clearassign ----

async def clearassign_command(update, context):
    if update.effective_user.id not in ADMIN_USER_IDS:
        msg = await update.message.reply_text("You don't have permission to do that.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    text = update.message.text
    if not _command_has_args(text):
        msg = await update.message.reply_text("Usage, /clearassign ddmmyy (e.g. for 8 Aug 2026 -> 060826)")
        asyncio.create_task(_delete_after(msg, 5))
        return

    raw = text.strip().split(maxsplit=1)[1]
    try:
        date_str = datetime.strptime(raw, "%d%m%y").date().isoformat()
    except ValueError:
        msg = await update.message.reply_text("Couldn't pase that date. Use ddmmyy, e.g. 060826.")
        asyncio.create_task(_delete_after(msg, 5))
        return

    boatstore.clear_date(date_str)
    msg = await update.message.reply_text(f"Cleared boat assignments for {renderer.format_date_label(date_str)}.")
    asyncio.create_task(_delete_after(msg, 5))


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


async def assign_date_choice(update, context):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_USER_IDS:
        await query.answer("Admins only.", show_alert=True)
        return
    await query.answer()

    _, date_str = query.data.split("|")
    timeslots = sorted(storage.get_by_date(date_str))

    context.chat_data["assign_date"] = date_str
    context.chat_data["assign_timeslots"] = timeslots
    context.chat_data["assign_ts_index"] = 0

    await _delete_message(context, query.message.chat_id, query.message.message_id)
    await _prompt_next_boat(context, query.message.chat_id)


async def assign_boat_choice(update, context):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_USER_IDS:
        await query.answer("Admins only.", show_alert=True)
        return
    await query.answer()

    _, boat = query.data.split("|", 1)
    chat_id = query.message.chat_id

    date_str = context.chat_data.get("assign_date")
    timeslot = context.chat_data.get("assign_timeslot")
    names = context.chat_data.get("assign_names")
    name_index = context.chat_data.get("assign_name_index")

    if date_str is None or timeslot is None or names is None or name_index is None:
        # Stale tap from a run that already finished or was overtaken.
        await _delete_message(context, chat_id, query.message.message_id)
        return

    name = names[name_index]
    boatstore.assign_boat(date_str, timeslot, name, boat)

    await _delete_message(context, chat_id, context.chat_data.pop("assign_prompt_msg_id", None))
    context.chat_data["assign_name_index"] = name_index + 1
    await _prompt_next_boat(context, chat_id)


async def post_init(app):
    await app.bot.set_my_commands([
        ("attendance_add", "add yourself to a training slot <name> <timeslot>"),
        ("attendance_remove", "remove yourself from a training slot <name> <timeslot>"),
    ])


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    add_conversation = ConversationHandler(
        entry_points=[CommandHandler("attendance_add", add_entry)],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_name)],
            ADD_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_timeslot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    remove_conversation = ConversationHandler(
        entry_points=[CommandHandler("attendance_remove", remove_entry)],
        states={
            REMOVE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_receive_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    coming_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(coming_entry, pattern=r"^coming\|")],
        states={
            COMING_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, coming_receive_timeslot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    info_add_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(info_add_entry, pattern=r"^info_add$")],
        states={
            INFO_ADD_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, info_add_receive_timeslot)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(info_add_conversation)
    app.add_handler(add_conversation)
    app.add_handler(remove_conversation)
    app.add_handler(coming_conversation)
    app.add_handler(CommandHandler("whereami", whereami))
    app.add_handler(CommandHandler("attendance_clear", clear_command))
    app.add_handler(CommandHandler("assign", assign_command))
    app.add_handler(CommandHandler("clearassign", clearassign_command))
    app.add_handler(CallbackQueryHandler(info_remove_entry, pattern=r"^info_remove$"))
    app.add_handler(CallbackQueryHandler(handle_date_choice, pattern=r"^add\|"))
    app.add_handler(CallbackQueryHandler(handle_remove_choice, pattern=r"^remove\|"))
    app.add_handler(CallbackQueryHandler(assign_date_choice, pattern=r"^assigndate\|"))
    app.add_handler(CallbackQueryHandler(assign_boat_choice, pattern=r"^assignboat\|"))
    app.add_handler(MessageHandler(filters.Regex(r"^!info$"), info_trigger))
    app.run_polling()


if __name__ == "__main__":
    main()
