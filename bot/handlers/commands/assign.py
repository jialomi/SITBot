import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler
from bot.common import ADMIN_USER_IDS, _delete_after
from bot import storage, renderer

async def assign_command(update, context):
    if update.effective_user.id not in ADMIN_USER_IDS:
        msg = await update.message.reply_text("You don't have permission to do that.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    data = storage.load()
    dates = sorted(d for d in data if data[d])
    if not dates:
        msg = await update.message.reply_text("No signups to assign boats for yet")
        asyncio.create_task(_delete_after(msg, 3))
        return

    buttons = [
        [InlineKeyboardButton(renderer.format_date_label(d), callback_data=f"assigndate|{d}")]
        for d in dates   
    ]
    await update.message.reply_text(
        "Assign boats for which date?", reply_markup=InlineKeyboardMarkup(buttons)
    )

handler = CommandHandler("assign", assign_command)