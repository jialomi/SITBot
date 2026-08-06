import asyncio
from telegram.ext import CommandHandler
from bot.common import ADMIN_USER_IDS, _delete_after
from bot import storage, boatstore, liststore

async def clear_command(update, context):
	if update.effective_user.id not in ADMIN_USER_IDS:
		msg = await update.message.reply_text("You don't have permission to do that.")
		asyncio.create_task(_delete_after(msg, 3))
		return

	storage.clear_all()
	boatstore.clear_all()
	liststore.clear_all()
	msg = await update.message.reply_text("All signups cleared")
	asyncio.create_task(_delete_after(msg, 3))
	try:
		await update.message.delete()
	except Exception:
		pass

handler = CommandHandler("attendance_clear", clear_command)