"""
handlers/templates.py — quick expense templates (⚡ Quick button).
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import TMPL_ACTION, TMPL_ADD_NAME, TMPL_ADD_AMOUNT, TMPL_ADD_CAT, TMPL_DEL
from db import get_settings, get_templates, add_template, del_template, add_expense, get_limit, get_month_spent
from i18n import tr, sym, cat_label, cat_key_from_label, T
from keyboards import main_kb, tmpl_kb, cat_kb, cancel_kb
from security import is_allowed, sanitize, parse_amount


async def tmpl_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s         = get_settings(uid)
    templates = get_templates(uid)
    await update.message.reply_text(
        tr(uid, "tmpl_none" if not templates else "tmpl_choose", s),
        reply_markup=tmpl_kb(uid, s, templates),
    )
    return TMPL_ACTION


async def tmpl_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid       = update.effective_user.id
    s         = get_settings(uid)
    text      = sanitize(update.message.text)
    templates = get_templates(uid)

    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if text == tr(uid, "btn_tmpl_add", s):
        await update.message.reply_text(tr(uid, "tmpl_add_name", s), reply_markup=cancel_kb(uid, s))
        return TMPL_ADD_NAME

    if text == tr(uid, "btn_tmpl_del", s):
        if not templates:
            await update.message.reply_text(tr(uid, "tmpl_no_del", s), reply_markup=main_kb(uid, s))
            return ConversationHandler.END
        rows = [[f"🗑 {t['name']}"] for t in templates]
        rows.append([tr(uid, "btn_cancel", s)])
        from telegram import ReplyKeyboardMarkup
        await update.message.reply_text(
            tr(uid, "tmpl_del_choose", s),
            reply_markup=ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True),
        )
        return TMPL_DEL

    # Quick-use a template
    _sym = sym(s)
    for t in templates:
        if text == f"⚡ {t['name']} ({float(t['amount']):.0f} {_sym})":
            add_expense(uid, float(t["amount"]), t["category"], t["name"])
            cl    = cat_label(s["language"], t["category"], uid)
            limit = get_limit(uid, t["category"])
            extra = ""
            if limit:
                spent = get_month_spent(uid, t["category"])
                if spent >= limit:
                    extra = "\n" + tr(uid, "limit_over", s, cat=cl, spent=spent, limit=limit, sym=_sym)
                elif spent >= limit * 0.8:
                    extra = "\n" + tr(uid, "limit_warn", s, cat=cl, spent=spent, limit=limit,
                                      pct=spent / limit * 100, sym=_sym)
            await update.message.reply_text(
                tr(uid, "saved", s, name=t["name"], amount=float(t["amount"]), sym=_sym, cat=cl) + extra,
                parse_mode="HTML", reply_markup=main_kb(uid, s),
            )
            return ConversationHandler.END

    await update.message.reply_text(tr(uid, "tmpl_choose", s), reply_markup=tmpl_kb(uid, s, templates))
    return TMPL_ACTION


async def tmpl_add_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    name = sanitize(update.message.text, 40)
    if name == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    ctx.user_data["tmpl_name"] = name
    await update.message.reply_text(
        tr(uid, "tmpl_add_amount", s, name=name, sym=sym(s)), reply_markup=cancel_kb(uid, s)
    )
    return TMPL_ADD_AMOUNT


async def tmpl_add_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    s      = get_settings(uid)
    text   = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    amount = parse_amount(text)
    if not amount:
        await update.message.reply_text(tr(uid, "bad_amount", s), reply_markup=cancel_kb(uid, s))
        return TMPL_ADD_AMOUNT
    ctx.user_data["tmpl_amt"] = amount
    await update.message.reply_text(
        tr(uid, "tmpl_add_cat", s, name=ctx.user_data["tmpl_name"]),
        reply_markup=cat_kb(uid, s),
    )
    return TMPL_ADD_CAT


async def tmpl_add_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    s     = get_settings(uid)
    label = sanitize(update.message.text)
    if label == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    key = cat_key_from_label(label, s["language"], uid)
    if not key:
        await update.message.reply_text(tr(uid, "choose_cat", s), reply_markup=cat_kb(uid, s))
        return TMPL_ADD_CAT
    name   = ctx.user_data["tmpl_name"]
    amount = ctx.user_data["tmpl_amt"]
    add_template(uid, name, amount, key)
    await update.message.reply_text(
        tr(uid, "tmpl_added", s, name=name, amount=amount, sym=sym(s), cat=label),
        reply_markup=main_kb(uid, s),
    )
    return ConversationHandler.END


async def tmpl_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    for t in get_templates(uid):
        if text == f"🗑 {t['name']}":
            del_template(t["id"])
            await update.message.reply_text(
                tr(uid, "tmpl_deleted", s, name=t["name"]), reply_markup=main_kb(uid, s)
            )
            return ConversationHandler.END
    await update.message.reply_text(tr(uid, "tmpl_del_choose", s))
    return TMPL_DEL


def make_tmpl_conv() -> ConversationHandler:
    import re as _re
    texts = [T[l].get("btn_quick") for l in T if T[l].get("btn_quick")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), tmpl_start)],
        states={
            TMPL_ACTION:     [MessageHandler(filters.TEXT & ~filters.COMMAND, tmpl_action)],
            TMPL_ADD_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, tmpl_add_name)],
            TMPL_ADD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tmpl_add_amount)],
            TMPL_ADD_CAT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, tmpl_add_cat)],
            TMPL_DEL:        [MessageHandler(filters.TEXT & ~filters.COMMAND, tmpl_del)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
