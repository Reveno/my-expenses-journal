"""
handlers/categories.py — user-defined expense categories.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import CCAT_MENU, CCAT_NAME, CCAT_DEL
from db import get_settings, get_custom_cats, add_custom_cat, del_custom_cat
from i18n import tr
from keyboards import main_kb, cancel_kb
from security import is_allowed, sanitize
from telegram import ReplyKeyboardMarkup


async def ccat_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s    = get_settings(uid)
    cats = get_custom_cats(uid)
    lines = [tr(uid, "ccat_header", s)]
    lines += [tr(uid, "ccat_list_item", s, label=c["label"]) for c in cats] or [tr(uid, "ccat_none", s)]
    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([
            [tr(uid, "btn_ccat_add", s), tr(uid, "btn_ccat_del", s)],
            [tr(uid, "btn_cancel", s)],
        ], resize_keyboard=True, one_time_keyboard=True),
    )
    return CCAT_MENU


async def ccat_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if text == tr(uid, "btn_ccat_add", s):
        await update.message.reply_text(tr(uid, "ccat_add_name", s), reply_markup=cancel_kb(uid, s))
        return CCAT_NAME
    if text == tr(uid, "btn_ccat_del", s):
        cats = get_custom_cats(uid)
        if not cats:
            await update.message.reply_text(tr(uid, "ccat_no_del", s), reply_markup=main_kb(uid, s))
            return ConversationHandler.END
        rows = [[c["label"]] for c in cats] + [[tr(uid, "btn_cancel", s)]]
        await update.message.reply_text(
            tr(uid, "ccat_del_choose", s),
            reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True),
        )
        return CCAT_DEL
    return CCAT_MENU


async def ccat_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if len(text) > 40:
        await update.message.reply_text(tr(uid, "ccat_too_long", s), reply_markup=cancel_kb(uid, s))
        return CCAT_NAME
    add_custom_cat(uid, text)
    await update.message.reply_text(tr(uid, "ccat_added", s, name=text), reply_markup=main_kb(uid, s))
    return ConversationHandler.END


async def ccat_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    for c in get_custom_cats(uid):
        if c["label"] == text:
            del_custom_cat(c["id"])
            await update.message.reply_text(tr(uid, "ccat_deleted", s, name=text), reply_markup=main_kb(uid, s))
            return ConversationHandler.END
    return CCAT_DEL


def make_ccat_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^⚙️ [МMM]"), ccat_start)],
        states={
            CCAT_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, ccat_menu)],
            CCAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ccat_name)],
            CCAT_DEL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ccat_del)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
