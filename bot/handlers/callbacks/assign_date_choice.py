from telegram.ext import CallbackQueryHandler

from bot.common import ADMIN_USER_IDS, _delete_message, _prompt_next_boat
from bot import storage


async def assign_date_choice(update, context):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_USER_IDS:
        await query.answer("Admins only.", show_alert=True)
        return
    await query.answer()

    _, date_str = query.data.split("|")
    timeslots = sorted(storage.get_by_date(date_str))

    context.chat_data["assign_date"] = date_str
    context.chat_data["assign_timeslots"] = timeslots
    context.chat_data["assign_ts_index"] = 0

    await _delete_message(context, query.message.chat_id, query.message.message_id)
    await _prompt_next_boat(context, query.message.chat_id)


handler = CallbackQueryHandler(assign_date_choice, pattern=r"^assigndate\|")
