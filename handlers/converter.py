"""
handlers/converter.py — inline currency converter (stays open for multiple conversions).
"""
import re
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import CONVERT
from db import get_settings
from i18n import tr, T
from keyboards import main_kb, cancel_kb
from currency import get_rates, convert_amount
from security import is_allowed, sanitize


async def convert_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "convert_prompt", s), parse_mode="HTML", reply_markup=cancel_kb(uid, s)
    )
    return CONVERT


async def convert_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text).strip()

    # Exit on any main menu button
    all_btns = {T[l][k] for l in T for k in T[l]}
    if text in all_btns and text != tr(uid, "btn_cancel", s):
        from handlers.core import cmd_start
        await update.message.reply_text(tr(uid, "choose_menu", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    m = re.match(r"([\d.,]+)\s+([A-Za-z]{3})\s+([A-Za-z]{3})", text)
    if not m:
        await update.message.reply_text(
            tr(uid, "convert_error", s), parse_mode="HTML", reply_markup=cancel_kb(uid, s)
        )
        return CONVERT

    try:
        amount = float(m.group(1).replace(",", "."))
    except ValueError:
        await update.message.reply_text(tr(uid, "convert_error", s), parse_mode="HTML")
        return CONVERT

    from_cur = m.group(2).upper()
    to_cur   = m.group(3).upper()
    rates    = await get_rates()

    if from_cur not in rates:
        await update.message.reply_text(tr(uid, "convert_unavail", s, cur=from_cur), parse_mode="HTML")
        return CONVERT
    if to_cur not in rates:
        await update.message.reply_text(tr(uid, "convert_unavail", s, cur=to_cur), parse_mode="HTML")
        return CONVERT

    result = convert_amount(amount, from_cur, to_cur, rates)
    rate_1 = convert_amount(1, from_cur, to_cur, rates)
    await update.message.reply_text(
        tr(uid, "convert_result", s,
           amount=amount, from_cur=from_cur, result=result, to_cur=to_cur, rate=rate_1),
        parse_mode="HTML", reply_markup=cancel_kb(uid, s),
    )
    return CONVERT  # stay open for more conversions


def make_converter_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔄"), convert_start)],
        states={CONVERT: [MessageHandler(filters.TEXT & ~filters.COMMAND, convert_do)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
