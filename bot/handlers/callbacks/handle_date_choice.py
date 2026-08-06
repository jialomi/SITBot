import asyncio

from telegram.ext import CallbackQueryHandler

from bot.common import _delete_after, _delete_message, _post_updated_list
from bot import storage


async def handle_date_choice(update, context):
    query = update.callback_query
    await query.answer()

    _, name, timeslot, date_str = query.data.split("|")
    storage.add(date_str, timeslot, name)

    await _post_updated_list(context, date_str)
    await _delete_message(context, query.message.chat_id, query.message.message_id)

    confirm = await context.bot.send_message(
        chat_id=query.message.chat_id,
        message_thread_id=query.message.message_thread_id,
        text="✅ Successfully added."
    )
    asyncio.create_task(_delete_after(confirm, 10))


handler = CallbackQueryHandler(handle_date_choice, pattern=r"^add\|")
