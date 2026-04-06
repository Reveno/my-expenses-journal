"""
handlers/reminders.py — per-user reminder schedule (inactivity, daily, weekly).
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import REMIND_MENU, REMIND_INACT, REMIND_DAILY, REMIND_WDAY, REMIND_WTIME
from db import get_settings, get_reminder_settings, save_reminder_settings
from i18n import tr
from keyboards import main_kb, remind_kb, cancel_kb
from security import is_allowed, sanitize


def _valid_hhmm(t: str) -> bool:
    parts = t.split(":")
    if len(parts) != 2:
        return False
    try:
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except ValueError:
        return False


def _status_text(uid: int, s: dict) -> str:
    rs  = get_reminder_settings(uid)
    off = tr(uid, "remind_off", s)
    return tr(uid, "remind_current", s,
              inact  = str(rs["inactive_days"]) if rs["inactive_days"] else off,
              daily  = rs["daily_time"]  or off,
              weekly = rs["weekly_time"] or off,
              wday   = str(rs["weekly_day"]) if rs["weekly_day"] is not None else off)


async def remind_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "remind_title", s) + "\n\n" + _status_text(uid, s),
        parse_mode="HTML", reply_markup=remind_kb(uid, s),
    )
    return REMIND_MENU


async def remind_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if text == tr(uid, "remind_btn_inactive", s):
        await update.message.reply_text(tr(uid, "remind_inactive_prompt", s), reply_markup=cancel_kb(uid, s))
        return REMIND_INACT
    if text == tr(uid, "remind_btn_daily", s):
        await update.message.reply_text(tr(uid, "remind_daily_prompt", s), reply_markup=cancel_kb(uid, s))
        return REMIND_DAILY
    if text == tr(uid, "remind_btn_weekly", s):
        await update.message.reply_text(tr(uid, "remind_weekly_day_prompt", s), reply_markup=cancel_kb(uid, s))
        return REMIND_WDAY
    await update.message.reply_text(
        tr(uid, "remind_title", s) + "\n\n" + _status_text(uid, s),
        parse_mode="HTML", reply_markup=remind_kb(uid, s),
    )
    return REMIND_MENU


async def remind_set_inact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    try:
        days = int(text)
        if not 0 <= days <= 30:
            raise ValueError
    except ValueError:
        await update.message.reply_text(tr(uid, "remind_bad_inactive", s), reply_markup=cancel_kb(uid, s))
        return REMIND_INACT
    save_reminder_settings(uid, inactive_days=days)
    await update.message.reply_text(tr(uid, "remind_saved", s), reply_markup=main_kb(uid, s))
    return ConversationHandler.END


async def remind_set_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text).strip()
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if text == "0":
        save_reminder_settings(uid, daily_time=None)
        await update.message.reply_text(tr(uid, "remind_saved", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if not _valid_hhmm(text):
        await update.message.reply_text(tr(uid, "remind_bad_time", s), reply_markup=cancel_kb(uid, s))
        return REMIND_DAILY
    h, m = text.split(":")
    save_reminder_settings(uid, daily_time=f"{int(h):02d}:{int(m):02d}")
    await update.message.reply_text(tr(uid, "remind_saved", s), reply_markup=main_kb(uid, s))
    return ConversationHandler.END


async def remind_set_wday(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text).strip()
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    try:
        day = int(text)
        if not -1 <= day <= 6:
            raise ValueError
    except ValueError:
        await update.message.reply_text(tr(uid, "remind_bad_wday", s), reply_markup=cancel_kb(uid, s))
        return REMIND_WDAY
    if day == -1:
        save_reminder_settings(uid, weekly_day=None, weekly_time=None)
        await update.message.reply_text(tr(uid, "remind_saved", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    ctx.user_data["rm_wday"] = day
    await update.message.reply_text(tr(uid, "remind_weekly_time_prompt", s), reply_markup=cancel_kb(uid, s))
    return REMIND_WTIME


async def remind_set_wtime(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text).strip()
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if not _valid_hhmm(text):
        await update.message.reply_text(tr(uid, "remind_bad_time", s), reply_markup=cancel_kb(uid, s))
        return REMIND_WTIME
    h, m = text.split(":")
    save_reminder_settings(uid,
                           weekly_day=ctx.user_data["rm_wday"],
                           weekly_time=f"{int(h):02d}:{int(m):02d}")
    await update.message.reply_text(tr(uid, "remind_saved", s), reply_markup=main_kb(uid, s))
    return ConversationHandler.END


def make_reminders_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔔"), remind_start)],
        states={
            REMIND_MENU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_menu)],
            REMIND_INACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_set_inact)],
            REMIND_DAILY: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_set_daily)],
            REMIND_WDAY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_set_wday)],
            REMIND_WTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remind_set_wtime)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
