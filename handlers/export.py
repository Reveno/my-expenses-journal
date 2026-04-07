"""
handlers/export.py — Excel report generation and download.
"""
import io
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import EXPORT_PERIOD
from db import get_settings, get_expenses, period_dates
from i18n import tr, T
from keyboards import main_kb, export_kb
from excel import build_xlsx, XLSX_OK
from security import is_allowed, sanitize


async def export_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(tr(uid, "export_period", s), reply_markup=export_kb(uid, s))
    return EXPORT_PERIOD


async def export_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)

    # Build period map first so export buttons take priority over escape
    period_map = {
        tr(uid, "export_btn_today", s): "day",
        tr(uid, "export_btn_week",  s): "week",
        tr(uid, "export_btn_month", s): "month",
        tr(uid, "export_btn_all",   s): "all",
    }
    period = period_map.get(text)

    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if not period:
        # Check if it's a main menu button
        main_btns = {T[l][k] for l in T for k in T[l] if not k.startswith("export_btn")}
        if text in main_btns:
            await update.message.reply_text(tr(uid, "choose_menu", s), reply_markup=main_kb(uid, s))
            return ConversationHandler.END
        await update.message.reply_text(tr(uid, "export_period", s), reply_markup=export_kb(uid, s))
        return EXPORT_PERIOD

    start, end = period_dates(period)
    rows = get_expenses(uid, start, end)

    if not rows:
        await update.message.reply_text(tr(uid, "export_empty", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if not XLSX_OK:
        await update.message.reply_text(tr(uid, "export_no_xlsx", s), parse_mode="HTML", reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    await update.message.reply_text(tr(uid, "export_sending", s))
    data = build_xlsx(uid, rows, s)
    if not data:
        await update.message.reply_text(tr(uid, "export_no_xlsx", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    await update.message.reply_document(
        document=io.BytesIO(data),
        filename=f"expenses_{period}.xlsx",
        reply_markup=main_kb(uid, s),
    )
    return ConversationHandler.END


def make_export_conv() -> ConversationHandler:
    import re as _re
    texts = [T[l].get("btn_export") for l in T if T[l].get("btn_export")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), export_start)],
        states={EXPORT_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, export_do)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
