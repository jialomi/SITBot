import asyncio

from telegram.ext import CommandHandler

from bot.common import ADMIN_USER_IDS, _delete_after, _delete_message
from bot.jobs.daily_list import post_daily_list

async def daily_command(update, context):
	chat_id = update.effective_chat.id
	thread_id = update.message.message_thread_id
	await _delete_message(context, chat_id, update.message.message_id)

	if update.effective_user.id not in ADMIN_USER_IDS:
		msg = await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text="You don't have permission to do that.")
		asyncio.create_task(_delete_after(msg, 3))
		return

	posted = await post_daily_list(context)
	text = "Daily list posted." if posted else "A list for tomorrow already exists - nothing posted"
	msg = await context.bot.send_message(chat_id=chat_id, message_thread_id=thread_id, text=text)
	asyncio.create_task(_delete_after(msg, 3))


handler = CommandHandler("daily", daily_command)