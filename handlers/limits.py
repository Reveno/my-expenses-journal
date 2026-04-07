"""
handlers/limits.py — per-category monthly spending limits.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import SET_LIMIT_CAT, SET_LIMIT_AMOUNT
from db import get_settings, get_limit, set_limit
from i18n import tr, sym, cat_key_from_label, T
from keyboards import main_kb, cat_kb, cancel_kb
from security import is_allowed, sanitize, parse_amount


async def limit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(tr(uid, "limit_choose", s), reply_markup=cat_kb(uid, s))
    return SET_LIMIT_CAT


async def limit_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    s     = get_settings(uid)
    text  = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    key = cat_key_from_label(text, s["language"], uid)
    if not key:
        await update.message.reply_text(tr(uid, "limit_choose", s), reply_markup=cat_kb(uid, s))
        return SET_LIMIT_CAT
    ctx.user_data["lim_cat"]       = key
    ctx.user_data["lim_cat_label"] = text
    cur = get_limit(uid, key)
    info = f" (зараз: {cur:.2f} {sym(s)})" if cur else ""
    await update.message.reply_text(
        tr(uid, "limit_enter", s, cat=text + info, sym=sym(s)),
        reply_markup=cancel_kb(uid, s),
    )
    return SET_LIMIT_AMOUNT


async def limit_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    s     = get_settings(uid)
    raw   = sanitize(update.message.text)
    if raw == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if raw in ("0", "0.0", "0,0"):
        amount = 0.0
    else:
        amount = parse_amount(raw)
        if not amount:
            await update.message.reply_text(tr(uid, "bad_amount", s), reply_markup=cancel_kb(uid, s))
            return SET_LIMIT_AMOUNT
    cat   = ctx.user_data["lim_cat"]
    label = ctx.user_data["lim_cat_label"]
    set_limit(uid, cat, amount)
    msg = tr(uid, "limit_removed" if amount == 0 else "limit_set", s,
             cat=label, amount=amount, sym=sym(s))
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=main_kb(uid, s))
    return ConversationHandler.END


def make_limits_conv() -> ConversationHandler:
    import re as _re
    texts = [T[l].get("btn_limit") for l in T if T[l].get("btn_limit")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), limit_start)],
        states={
            SET_LIMIT_CAT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, limit_category)],
            SET_LIMIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, limit_amount)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
