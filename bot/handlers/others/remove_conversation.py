import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import (
    REMOVE_NAME, _delete_after, _delete_message, _command_has_args,
    _do_remove, _post_updated_list, cancel,
)
from bot import parser, storage, boatstore, renderer


async def remove_entry(update, context):
    text = update.message.text
    if not _command_has_args(text):
        prompt = await update.message.reply_text("Who do you want to remove? Type a name.")
        context.user_data["prompt_msg_id"] = prompt.message_id
        context.user_data["remove_command_msg_id"] = update.message.message_id
        return REMOVE_NAME

    try:
        parsed = parser.parse_remove(text)
    except ValueError as e:
        msg = await update.message.reply_text(str(e))
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    await _do_remove(context, update.effective_chat.id, parsed["name"], parsed["timeslot"])
    await _delete_message(context, update.effective_chat.id, update.message.message_id)
    return ConversationHandler.END


async def remove_receive_name(update, context):
    name = update.message.text.strip()
    chat_id = update.effective_chat.id

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    command_msg_id = context.user_data.pop("remove_command_msg_id", None)
    context.user_data.clear()
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)
    await _delete_message(context, chat_id, command_msg_id)

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


handler = ConversationHandler(
    entry_points=[CommandHandler("attendance_remove", remove_entry)],
    states={
        REMOVE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_receive_name)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
