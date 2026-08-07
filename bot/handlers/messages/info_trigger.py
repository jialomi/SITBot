from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters

from bot.common import ATTENDANCE_CHAT_ID, ATTENDANCE_INFO_THREAD_ID, INFO_TEXT


async def info_trigger(update, context):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Add Attendance", callback_data="info_add"),
            InlineKeyboardButton("Remove Attendance", callback_data="info_remove"),
        ],
        [
            InlineKeyboardButton("Crew", callback_data="crew"),
        ],
    ])
    await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID),
        message_thread_id=int(ATTENDANCE_INFO_THREAD_ID),
        text=INFO_TEXT,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


handler = MessageHandler(filters.Regex(r"^!info$"), info_trigger)
