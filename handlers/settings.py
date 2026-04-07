"""
handlers/settings.py — settings menu, language, currency, help, donate.
"""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import LANG_SELECT, CURR_PRIMARY, CURR_SECONDARY, SETTINGS_MENU, DONATE_URL, LANG_BUTTONS, CURRENCY_BUTTONS
from db import get_settings, save_settings
from i18n import tr, sym, T
from keyboards import main_kb, lang_kb, curr_kb, settings_kb, cancel_kb
from security import is_allowed, sanitize


# ── Settings menu ─────────────────────────────────────────────────────────────
async def settings_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "settings_title", s), parse_mode="HTML",
        reply_markup=settings_kb(uid, s),
    )
    return SETTINGS_MENU


async def settings_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)

    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if text == tr(uid, "btn_lang", s):
        await update.message.reply_text(tr(uid, "lang_select", s), reply_markup=lang_kb(uid, s))
        return LANG_SELECT

    if text == tr(uid, "btn_currency", s):
        await update.message.reply_text(
            tr(uid, "curr_primary", s), parse_mode="HTML",
            reply_markup=curr_kb(uid, s, with_none=False),
        )
        return CURR_PRIMARY

    if text == tr(uid, "btn_donate", s):
        if not DONATE_URL:
            await update.message.reply_text(tr(uid, "donate_no_url", s), reply_markup=main_kb(uid, s))
        else:
            await update.message.reply_text(
                tr(uid, "donate_msg", s, url=DONATE_URL),
                parse_mode="HTML", reply_markup=main_kb(uid, s),
                disable_web_page_preview=True,
            )
        return ConversationHandler.END

    await update.message.reply_text(
        tr(uid, "settings_title", s), parse_mode="HTML",
        reply_markup=settings_kb(uid, s),
    )
    return SETTINGS_MENU


async def lang_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid      = update.effective_user.id
    s        = get_settings(uid)
    text     = sanitize(update.message.text)
    lang_map = {v: k for k, v in LANG_BUTTONS.items()}
    if text not in lang_map:
        await update.message.reply_text(tr(uid, "lang_select", s), reply_markup=lang_kb(uid, s))
        return LANG_SELECT
    save_settings(uid, language=lang_map[text])
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "lang_switched", s), parse_mode="HTML", reply_markup=main_kb(uid, s)
    )
    return ConversationHandler.END


async def curr_primary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid     = update.effective_user.id
    s       = get_settings(uid)
    text    = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    cur_map = {v: k for k, v in CURRENCY_BUTTONS.items()}
    if text not in cur_map:
        await update.message.reply_text(
            tr(uid, "curr_primary", s), parse_mode="HTML",
            reply_markup=curr_kb(uid, s),
        )
        return CURR_PRIMARY
    chosen = cur_map[text]
    save_settings(uid, primary_currency=chosen)
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "curr_set_primary", s, cur=chosen, sym=sym(s)), parse_mode="HTML"
    )
    await update.message.reply_text(
        tr(uid, "curr_secondary", s), parse_mode="HTML",
        reply_markup=curr_kb(uid, s, with_none=True),
    )
    return CURR_SECONDARY


async def curr_secondary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid     = update.effective_user.id
    s       = get_settings(uid)
    text    = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    if text == tr(uid, "curr_none", s):
        save_settings(uid, secondary_currency=None)
        s = get_settings(uid)
        await update.message.reply_text(tr(uid, "curr_set_secondary_none", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    cur_map = {v: k for k, v in CURRENCY_BUTTONS.items()}
    if text not in cur_map:
        await update.message.reply_text(
            tr(uid, "curr_secondary", s), parse_mode="HTML",
            reply_markup=curr_kb(uid, s, with_none=True),
        )
        return CURR_SECONDARY
    chosen = cur_map[text]
    save_settings(uid, secondary_currency=chosen)
    s = get_settings(uid)
    from config import CURRENCY_SYMBOLS
    sec_sym = CURRENCY_SYMBOLS.get(chosen, chosen)
    await update.message.reply_text(
        tr(uid, "curr_set_secondary", s, cur=chosen, sym=sec_sym),
        parse_mode="HTML", reply_markup=main_kb(uid, s),
    )
    return ConversationHandler.END


def make_settings_conv() -> ConversationHandler:
    import re as _re
    texts = [T[l].get("btn_settings") for l in T if T[l].get("btn_settings")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), settings_start)],
        states={
            SETTINGS_MENU:  [MessageHandler(filters.TEXT & ~filters.COMMAND, settings_menu)],
            LANG_SELECT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, lang_select)],
            CURR_PRIMARY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, curr_primary)],
            CURR_SECONDARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, curr_secondary)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )


# ── Help ──────────────────────────────────────────────────────────────────────
async def show_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "help_text", s), parse_mode="HTML",
        reply_markup=main_kb(uid, s),
        disable_web_page_preview=True,
    )
