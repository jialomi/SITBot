from telegram.ext import MessageHandler, filters

from bot.common import ATTENDANCE_CHAT_ID, ATTENDANCE_INFO_THREAD_ID, INFO_TEXT


async def info_trigger(update, context):
    await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID),
        message_thread_id=int(ATTENDANCE_INFO_THREAD_ID),
        text=INFO_TEXT,
        parse_mode="HTML",
    )


handler = MessageHandler(filters.Regex(r"^!info$"), info_trigger)
