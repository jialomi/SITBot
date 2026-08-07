import asyncio

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import (
    CREW_NAME, CREW_TIMESLOT, _delete_after, _delete_message, _send_date_picker,
    _post_updated_list, cancel,
)
from bot import parser, storage


async def crew_entry(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    # "crew" (from INFO topic) has no date attached, so the date picker
    # still runs at the end. "crew|<date>" (from a posted list) is tied
    # to that specific date, skipping the picker entirely.
    parts = query.data.split("|")
    crew_date = parts[1] if len(parts) > 1 else None

    prompt = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text="If K2 put partner1/partner2 (e.g. jer/glenn) if K4 (e.g. jer/jw/gab/jos) short form name will do."
    )
    context.user_data["crew_thread_id"] = thread_id
    context.user_data["crew_date"] = crew_date
    context.user_data["prompt_msg_id"] = prompt.message_id
    return CREW_NAME


async def crew_receive_name(update, context):
    context.user_data["crew_name"] = update.message.text.strip()
    context.user_data["crew_name_msg_id"] = update.message.message_id

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, update.effective_chat.id, prev_prompt_id)

    prompt = await update.message.reply_text("What timeslot? (e.g. 0700 or 7am)")
    context.user_data["prompt_msg_id"] = prompt.message_id
    return CREW_TIMESLOT


async def crew_receive_timeslot(update, context):
    raw = update.message.text.strip()
    try:
        timeslot = parser.normalize_timeslot(raw)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        await _delete_message(context, update.effective_chat.id, update.message.message_id)
        return CREW_TIMESLOT

    chat_id = update.effective_chat.id
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    await _delete_message(context, chat_id, prev_prompt_id)

    name_msg_id = context.user_data.pop("crew_name_msg_id", None)
    await _delete_message(context, chat_id, name_msg_id)
    await _delete_message(context, chat_id, update.message.message_id)

    name = context.user_data.pop("crew_name", None)
    thread_id = context.user_data.pop("crew_thread_id", None)
    crew_date = context.user_data.pop("crew_date", None)

    if crew_date:
        storage.add(crew_date, timeslot, name)
        await _post_updated_list(context, crew_date)

        confirm = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id, text="✅ Successfully added."
        )
        asyncio.create_task(_delete_after(confirm, 5))
    else:
        await _send_date_picker(context, chat_id, name, timeslot, thread_id=thread_id)

    return ConversationHandler.END


handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(crew_entry, pattern=r"^crew$"),
        CallbackQueryHandler(crew_entry, pattern=r"^crew\|"),
    ],
    states={
        CREW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, crew_receive_name)],
        CREW_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, crew_receive_timeslot)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)