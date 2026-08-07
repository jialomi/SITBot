from datetime import date, timedelta, time as dt_time
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot import renderer, liststore
from bot.common import ATTENDANCE_CHAT_ID, ATTENDANCE_LIST_THREAD_ID

async def post_daily_list(context):
    """Runs once a day: posts an empty list (with a 'Coming' button) for
    tomorrow, unless one's already been posted (e.g. someone already
    signed up before this job ran)."""
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()

    if liststore.get_message_id(tomorrow_str):
        return

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Coming", callback_data=f"coming|{tomorrow_str}"),
                InlineKeyboardButton("Remove Me", callback_data=f"removeme|{tomorrow_str}"),
            ],
            [
                InlineKeyboardButton("Crew", callback_data=f"crew|{tomorrow_str}")
            ],
        ]
    )
    msg = await context.bot.send_message(
        chat_id=int(ATTENDANCE_CHAT_ID), message_thread_id=int(ATTENDANCE_LIST_THREAD_ID),
        text=renderer.render(tomorrow_str, {}), reply_markup=keyboard,
    )
    liststore.set_message_id(tomorrow_str, msg.message_id)

job = {
    "callback": post_daily_list,
    "time": dt_time(hour=2, minute=23, tzinfo=ZoneInfo("Asia/Singapore")),
    "name": "post_daily_list"
}