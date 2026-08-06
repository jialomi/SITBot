from telegram.ext import CallbackQueryHandler

from bot.common import ADMIN_USER_IDS, _delete_message, _prompt_next_boat
from bot import boatstore


async def assign_boat_choice(update, context):
    query = update.callback_query
    if update.effective_user.id not in ADMIN_USER_IDS:
        await query.answer("Admins only.", show_alert=True)
        return
    await query.answer()

    _, boat = query.data.split("|", 1)
    chat_id = query.message.chat_id

    date_str = context.chat_data.get("assign_date")
    timeslot = context.chat_data.get("assign_timeslot")
    names = context.chat_data.get("assign_names")
    name_index = context.chat_data.get("assign_name_index")

    if date_str is None or timeslot is None or names is None or name_index is None:
        # Stale tap from a run that already finished or was overtaken.
        await _delete_message(context, chat_id, query.message.message_id)
        return

    name = names[name_index]
    boatstore.assign_boat(date_str, timeslot, name, boat)

    await _delete_message(context, chat_id, context.chat_data.pop("assign_prompt_msg_id", None))
    context.chat_data["assign_name_index"] = name_index + 1
    await _prompt_next_boat(context, chat_id)


handler = CallbackQueryHandler(assign_boat_choice, pattern=r"^assignboat\|")
