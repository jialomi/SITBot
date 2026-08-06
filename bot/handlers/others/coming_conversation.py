import asyncio
from datetime import date

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import (
    COMING_TIMESLOT, ATTENDANCE_LIST_THREAD_ID, _delete_after, _delete_message,
    _post_updated_list, cancel,
)
from bot import parser, storage


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


handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(coming_entry, pattern=r"^coming\|")],
    states={
        COMING_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, coming_receive_timeslot)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
