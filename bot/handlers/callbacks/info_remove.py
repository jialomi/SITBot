import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

from bot.common import _delete_after, _post_updated_list
from bot import storage, boatstore, renderer


async def info_remove_entry(update, context):
    query = update.callback_query
    await query.answer()

    name = query.from_user.first_name
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    entries = storage.find_entries(name)

    if not entries:
        msg = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id,
            text=f"{name} wasn't found on any upcoming slots"
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


handler = CallbackQueryHandler(info_remove_entry, pattern=r"^info_remove$")
