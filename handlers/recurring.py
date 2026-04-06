"""
handlers/recurring.py — recurring monthly expenses (auto-recorded by scheduler).
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import RECUR_MENU, RECUR_NAME, RECUR_AMT, RECUR_CAT, RECUR_DAY, RECUR_DEL
from db import get_settings, get_recurring, add_recurring, del_recurring
from i18n import tr, sym, cat_key_from_label
from keyboards import main_kb, recur_kb, recur_del_kb, cat_kb, cancel_kb
from security import is_allowed, sanitize, parse_amount


async def recur_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s     = get_settings(uid)
    items = get_recurring(uid)
    text  = tr(uid, "recur_choose" if items else "recur_none", s)
    await update.message.reply_text(text, reply_markup=recur_kb(uid, s, items))
    return RECUR_MENU


async def recur_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if text == tr(uid, "btn_recur_add", s):
        await update.message.reply_text(tr(uid, "recur_add_name", s), reply_markup=cancel_kb(uid, s))
        return RECUR_NAME
    if text == tr(uid, "btn_recur_del", s):
        items = get_recurring(uid)
        if not items:
            await update.message.reply_text(tr(uid, "recur_no_del", s), reply_markup=main_kb(uid, s))
            return ConversationHandler.END
        await update.message.reply_text(
            tr(uid, "recur_del_choose", s), reply_markup=recur_del_kb(uid, s, items)
        )
        return RECUR_DEL
    items = get_recurring(uid)
    await update.message.reply_text(tr(uid, "recur_choose", s), reply_markup=recur_kb(uid, s, items))
    return RECUR_MENU


async def recur_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    name = sanitize(update.message.text, 50)
    if name == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    ctx.user_data["rc_name"] = name
    await update.message.reply_text(
        tr(uid, "recur_add_amount", s, name=name, sym=sym(s)), reply_markup=cancel_kb(uid, s)
    )
    return RECUR_AMT


async def recur_amt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    s      = get_settings(uid)
    amount = parse_amount(update.message.text)
    if not amount:
        await update.message.reply_text(tr(uid, "bad_amount", s), reply_markup=cancel_kb(uid, s))
        return RECUR_AMT
    ctx.user_data["rc_amt"] = amount
    await update.message.reply_text(
        tr(uid, "recur_add_cat", s, name=ctx.user_data["rc_name"]),
        reply_markup=cat_kb(uid, s),
    )
    return RECUR_CAT


async def recur_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    s     = get_settings(uid)
    label = sanitize(update.message.text)
    if label == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    key = cat_key_from_label(label, s["language"], uid)
    if not key:
        await update.message.reply_text(tr(uid, "choose_cat", s), reply_markup=cat_kb(uid, s))
        return RECUR_CAT
    ctx.user_data["rc_cat"] = key
    await update.message.reply_text(tr(uid, "recur_add_day", s), reply_markup=cancel_kb(uid, s))
    return RECUR_DAY


async def recur_day(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    try:
        day = int(text)
        if not 1 <= day <= 31:
            raise ValueError
    except ValueError:
        await update.message.reply_text(tr(uid, "recur_bad_day", s), reply_markup=cancel_kb(uid, s))
        return RECUR_DAY
    name   = ctx.user_data["rc_name"]
    amount = ctx.user_data["rc_amt"]
    cat    = ctx.user_data["rc_cat"]
    add_recurring(uid, name, amount, cat, day)
    await update.message.reply_text(
        tr(uid, "recur_added", s, name=name, day=day, amount=amount, sym=sym(s)),
        reply_markup=main_kb(uid, s),
    )
    return ConversationHandler.END


async def recur_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    for item in get_recurring(uid):
        if text == f"🗑 {item['name']}":
            del_recurring(item["id"])
            await update.message.reply_text(
                tr(uid, "recur_deleted", s, name=item["name"]), reply_markup=main_kb(uid, s)
            )
            return ConversationHandler.END
    return RECUR_DEL


def make_recur_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🔁"), recur_start)],
        states={
            RECUR_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_menu)],
            RECUR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_name)],
            RECUR_AMT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_amt)],
            RECUR_CAT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_cat)],
            RECUR_DAY:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_day)],
            RECUR_DEL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, recur_del)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
