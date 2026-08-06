import asyncio

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import INFO_ADD_TIMESLOT, _delete_after, _delete_message, _send_date_picker, cancel
from bot import parser


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


handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(info_add_entry, pattern=r"^info_add$")],
    states={
        INFO_ADD_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, info_add_receive_timeslot)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
