from telegram.ext import CommandHandler

async def whereami(update, context):
	chat_id = update.effective_chat.id
	thread_id = update.message.message_thread_id
	await update.message.reply_text(f"chat_id: {chat_id}\nmessage_thread_id: {thread_id}")

handler = CommandHandler("whereami", whereami)