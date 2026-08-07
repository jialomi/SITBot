import asyncio
from datetime import date, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest

from bot import storage, renderer, boatstore, liststore
from .config import ATTENDANCE_CHAT_ID, ATTENDANCE_LIST_THREAD_ID
from .helpers import _delete_after, _delete_message


async def _send_date_picker(context, chat_id, name, timeslot, thread_id=None):
    buttons = []
    labels = ["Today", "Tomorrow"]
    for offset in range(2):
        d = date.today() + timedelta(days=offset)
        d_iso = d.isoformat()
        label = f"{labels[offset]} ({d.day} {d.strftime('%b')} {d.year})"
        callback_data = f"add|{name}|{timeslot}|{d_iso}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback_data)])

    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text="Pick a date:", reply_markup=keyboard)


async def _post_updated_list(context, date_str):
    """Keeps one message per date, edited in place. Sends a new message only
    the first time a date gets a signup; edits it on every add/remove after
    that. If the date ends up with no signups, the message is deleted."""
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
