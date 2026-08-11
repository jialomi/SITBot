import asyncio

from telegram.ext import ConversationHandler


async def _delete_after(msg, seconds):
    await asyncio.sleep(seconds)
    try:
        await msg.delete()
    except Exception:
        pass


async def _delete_message(context, chat_id, message_id):
    if message_id is None:
        return
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def _command_has_args(text):
    """True if there's anything after the command word itself."""
    return len(text.strip().split()) > 1


async def cancel(update, context):
    chat_id = update.effective_chat.id
    thread_id = update.message.message_thread_id
    prev_prompt_id = context.user_data.pop("prompt_msg_id", None)
    context.user_data.clear()
    await _delete_message(context, chat_id, prev_prompt_id)
    await _delete_message(context, chat_id, update.message.message_id)
    msg = await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text="Cancelled.")
    asyncio.create_task(_delete_after(msg, 3))
    return ConversationHandler.END
