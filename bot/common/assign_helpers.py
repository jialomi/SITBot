import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot import storage, renderer, boatstore
from .helpers import _delete_after


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
