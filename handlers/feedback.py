"""
handlers/feedback.py — user feedback system with admin /reply command.
Rate-limited to 1 message per hour per user.
"""
import time
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import FEEDBACK_MSG, ADMIN_ID
from db import get_settings
from i18n import tr, T
from keyboards import main_kb, cancel_kb
from security import is_allowed, sanitize

log = logging.getLogger(__name__)
_cooldown: dict[int, float] = {}  # uid → last feedback timestamp


async def feedback_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(tr(uid, "feedback_prompt", s), reply_markup=cancel_kb(uid, s))
    return FEEDBACK_MSG


async def feedback_got_msg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text, 1000)

    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    # Rate limit: 1 message per hour
    now = time.time()
    if now - _cooldown.get(uid, 0) < 3600:
        await update.message.reply_text(tr(uid, "feedback_cooldown", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    _cooldown[uid] = now

    user     = update.effective_user
    name     = (user.full_name or "").strip() or f"User {uid}"
    username = f"@{user.username}" if user.username else "—"

    if ADMIN_ID:
        try:
            admin_text = (
                f"{tr(uid, 'feedback_received', s, name=name, user_id=uid, text=text)}\n"
                f"Username: {username}\n\n"
                f"<i>Reply: /reply {uid} your text here</i>"
            )
            await ctx.bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")
        except Exception as e:
            log.warning("Could not send feedback to admin: %s", e)

    await update.message.reply_text(tr(uid, "feedback_sent", s), reply_markup=main_kb(uid, s))
    return ConversationHandler.END


async def cmd_reply(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin command: /reply USER_ID message text"""
    sender = update.effective_user.id
    if sender != ADMIN_ID:
        return
    parts = update.message.text.split(maxsplit=2)
    s     = get_settings(sender)
    if len(parts) < 3:
        await update.message.reply_text(tr(sender, "feedback_reply_usage", s))
        return
    try:
        target_uid = int(parts[1])
    except ValueError:
        await update.message.reply_text(tr(sender, "feedback_reply_usage", s))
        return
    reply_text = parts[2]
    s_target   = get_settings(target_uid)
    try:
        await ctx.bot.send_message(
            chat_id=target_uid,
            text=tr(target_uid, "feedback_reply", s_target, text=reply_text),
            parse_mode="HTML",
        )
        await update.message.reply_text(tr(sender, "feedback_reply_sent", s, uid=target_uid))
    except Exception:
        await update.message.reply_text(tr(sender, "feedback_reply_fail", s))


def make_feedback_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^💬"), feedback_start)],
        states={FEEDBACK_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_got_msg)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
