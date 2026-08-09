import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from bot.common import REMOVE_OTHER_NAME, _delete_after, _delete_message, _post_updated_list, cancel
from bot import storage, boatstore


async def remove_other_entry(update, context):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    thread_id = query.message.message_thread_id

    _, date_str = query.data.split("|")

    prompt = await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text="Who do you want to remove? Type a name."
    )
    context.user_data["remove_other_date"] = date_str
    context.user_data["remove_other_thread_id"] = thread_id
    context.user_data["prompt_msg_id"] = prompt.message_id
    return REMOVE_OTHER_NAME


async def remove_other_receive_name(update, context):
    name = update.message.text.strip()
    chat_id = update.effective_chat.id

    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    date_str = context.user_data.pop("remove_other_date", None)
    thread_id = context.user_data.pop("remove_other_thread_id", None)
    context.user_data.clear()
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)

    slots = storage.get_by_date(date_str)
    matches = [ts for ts, names in slots.items() if name in names]

    if not matches:
        msg = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id,
            text=f"{name} wasn't found on this date's list"
        )
        asyncio.create_task(_delete_after(msg, 10))
        return ConversationHandler.END

    if len(matches) == 1:
        timeslot = matches[0]
        storage.remove_specific(name, date_str, timeslot)
        boatstore.remove_assignment(date_str, timeslot, name)
        await _post_updated_list(context, date_str)

        confirm = await context.bot.send_message(
            chat_id=chat_id, message_thread_id=thread_id, text="✅ Successfully removed."
        )
        asyncio.create_task(_delete_after(confirm, 5))
        return ConversationHandler.END

    buttons = []
    for timeslot in matches:
        callback_data = f"remove|{name}|{date_str}|{timeslot}"
        buttons.append([InlineKeyboardButton(timeslot, callback_data=callback_data)])
    keyboard = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=chat_id, message_thread_id=thread_id,
        text=f"{name} is on this date more than once - which one?", reply_markup=keyboard
    )
    return ConversationHandler.END

handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(remove_other_entry, pattern="^removeother\|")],
    states={
        REMOVE_OTHER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_other_receive_name)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)