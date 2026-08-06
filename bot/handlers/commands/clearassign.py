import asyncio
from datetime import datetime

from telegram.ext import CommandHandler

from bot.common import ADMIN_USER_IDS, _delete_after, _command_has_args
from bot import boatstore, renderer


async def clearassign_command(update, context):
    if update.effective_user.id not in ADMIN_USER_IDS:
        msg = await update.message.reply_text("You don't have permission to do that.")
        asyncio.create_task(_delete_after(msg, 3))
        return

    text = update.message.text
    if not _command_has_args(text):
        msg = await update.message.reply_text("Usage, /clearassign ddmmyy (e.g. for 8 Aug 2026 -> 060826)")
        asyncio.create_task(_delete_after(msg, 5))
        return

    raw = text.strip().split(maxsplit=1)[1]
    try:
        date_str = datetime.strptime(raw, "%d%m%y").date().isoformat()
    except ValueError:
        msg = await update.message.reply_text("Couldn't parse that date. Use ddmmyy, e.g. 060826.")
        asyncio.create_task(_delete_after(msg, 5))
        return

    boatstore.clear_date(date_str)
    msg = await update.message.reply_text(f"Cleared boat assignments for {renderer.format_date_label(date_str)}.")
    asyncio.create_task(_delete_after(msg, 5))


handler = CommandHandler("clearassign", clearassign_command)
