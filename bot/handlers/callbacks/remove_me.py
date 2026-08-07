import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from bot.common import _delete_after, _post_updated_list
from bot import storage, boatstore

async def remove_me_entry(update, context):
    query = update.callback_query
    await query.answer()

    _, date_str, = query.data.split("|")
    name = query.from_user.first_name
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    slots = storage.get_by_date(date_str)
    matches = [ts for ts, names in slots.items() if name in names]

    if not matches:
        msg = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id,
            text=f"{name}, you're not on this date's list"
        )
        asyncio.create_task(_delete_after(msg, 10))
        return

    if len(matches) == 1:
        timeslot = matches[0]
        storage.remove_specific(name, date_str, timeslot)
        boatstore.remove_assignment(date_str, timeslot, name)
        await _post_updated_list(context, date_str)

        confirm = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id, text="✅ Successfully removed."
        )
        asyncio.create_task(_delete_after(confirm, 5))
        return

    buttons = []
    for timeslot in matches:
        callback_data = f"remove|{name}|{date_str}|{timeslot}"
        buttons.append([InlineKeyboardButton(timeslot, callback_data=callback_data)])
    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text="You're on this date more than once - which one?", reply_markup=keyboard
    )

handler = CallbackQueryHandler(remove_me_entry, pattern=r"^removeme\|")
