import asyncio

from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import (
    ADD_NAME, ADD_TIMESLOT, _delete_after, _delete_message, _command_has_args,
    _send_date_picker, cancel,
)
from bot import parser


async def add_entry(update, context):
    text = update.message.text
    if not _command_has_args(text):
        prompt = await update.message.reply_text("Who's this for? Type a name.")
        context.user_data["prompt_msg_id"] = prompt.message_id
        context.user_data["add_command_msg_id"] = update.message.message_id
        return ADD_NAME

    try:
        parsed = parser.parse_add(text)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    await _send_date_picker(
        context, update.effective_chat.id, parsed["name"], parsed["timeslot"],
        thread_id=update.message.message_thread_id,
    )
    await _delete_message(context, update.effective_chat.id, update.message.message_id)
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

    command_msg_id = context.user_data.pop("add_command_msg_id", None)
    await _delete_message(context, update.effective_chat.id, command_msg_id)

    name = context.user_data.pop("add_name", None)
    await _send_date_picker(
        context, update.effective_chat.id, name, timeslot,
        thread_id=update.message.message_thread_id,
    )
    return ConversationHandler.END


handler = ConversationHandler(
    entry_points=[CommandHandler("attendance_add", add_entry)],
    states={
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_name)],
        ADD_TIMESLOT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_receive_timeslot)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
