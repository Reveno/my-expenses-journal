"""
handlers/menus.py — Finance, Reports, More submenu handlers.
Each submenu is a ConversationHandler that keeps the user inside
the submenu until they press Back.
"""
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters,
)
from config import (
    FINANCE_MENU, REPORTS_MENU, MORE_MENU,
    INCOME_AMT, INCOME_SRC, EXPORT_PERIOD,
)
from db import get_settings, add_income, get_month_income, get_month_expenses_total
from i18n import tr, sym, month_name, T
from keyboards import main_kb, finance_kb, reports_kb, more_kb, cancel_kb
from security import is_allowed, sanitize, parse_amount


# ── helpers ───────────────────────────────────────────────────────────────────
def _is_back(text: str) -> bool:
    return any(text == T[l].get("btn_back", "") for l in T)


# ── Finance submenu ───────────────────────────────────────────────────────────
async def finance_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s    = get_settings(uid)
    lang = s["language"]
    _sym = sym(s)
    now  = datetime.now()

    mn = month_name(now.month, now.year, lang)
    income_total   = get_month_income(uid)
    expenses_total = get_month_expenses_total(uid)
    balance        = income_total - expenses_total

    lines = [tr(uid, "finance_title", s, month=mn), ""]
    if income_total > 0:
        lines.append(tr(uid, "balance_income",   s, amount=income_total,   sym=_sym))
    else:
        lines.append(tr(uid, "finance_no_income", s))
    lines.append(tr(uid, "balance_expenses", s, amount=expenses_total, sym=_sym))
    if income_total > 0:
        lines.append("")
        lines.append(tr(uid,
            "balance_result_pos" if balance >= 0 else "balance_result_neg",
            s, amount=abs(balance), sym=_sym))
    lines.append("")
    lines.append(tr(uid, "finance_add_income_hint", s))

    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=finance_kb(uid, s)
    )
    return FINANCE_MENU


async def finance_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)

    if _is_back(text):
        await update.message.reply_text(tr(uid, "choose_menu", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    if any(text == T[l].get("btn_add_income_short", "") for l in T):
        await update.message.reply_text(
            tr(uid, "income_enter_amount", s, sym=sym(s)),
            parse_mode="HTML", reply_markup=cancel_kb(uid, s),
        )
        ctx.user_data["after_income"] = "finance"
        return INCOME_AMT

    return FINANCE_MENU


async def income_got_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    s      = get_settings(uid)
    text   = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        after = ctx.user_data.pop("after_income", None)
        kb    = finance_kb(uid, s) if after == "finance" else main_kb(uid, s)
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=kb)
        return ConversationHandler.END
    amount = parse_amount(text)
    if not amount:
        await update.message.reply_text(tr(uid, "bad_amount", s), reply_markup=cancel_kb(uid, s))
        return INCOME_AMT
    ctx.user_data["inc_amt"] = amount
    await update.message.reply_text(tr(uid, "income_enter_source", s), reply_markup=cancel_kb(uid, s))
    return INCOME_SRC


async def income_got_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    s      = get_settings(uid)
    source = sanitize(update.message.text, 60)
    if source == tr(uid, "btn_cancel", s):
        after = ctx.user_data.pop("after_income", None)
        kb    = finance_kb(uid, s) if after == "finance" else main_kb(uid, s)
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=kb)
        return ConversationHandler.END
    amount = ctx.user_data.pop("inc_amt", 0)
    after  = ctx.user_data.pop("after_income", None)
    add_income(uid, amount, source)
    kb = finance_kb(uid, s) if after == "finance" else main_kb(uid, s)
    await update.message.reply_text(
        tr(uid, "income_saved", s, source=source, amount=amount, sym=sym(s)),
        parse_mode="HTML", reply_markup=kb,
    )
    return ConversationHandler.END


def make_finance_conv() -> ConversationHandler:
    import re as _re
    texts   = [T[l]["btn_finance"] for l in T if T[l].get("btn_finance")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), finance_menu)],
        states={
            FINANCE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, finance_action)],
            INCOME_AMT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, income_got_amount)],
            INCOME_SRC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, income_got_source)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )


# ── Reports submenu ───────────────────────────────────────────────────────────
async def reports_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text("📊", reply_markup=reports_kb(uid, s))
    return REPORTS_MENU


async def reports_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)

    if _is_back(text):
        await update.message.reply_text(tr(uid, "choose_menu", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    from handlers.core import (summary_day, summary_week, summary_month,
                                top_categories, top_items, compare_months)

    kb      = reports_kb(uid, s)
    handled = False
    for lang in T:
        if text == T[lang].get("btn_today"):
            await summary_day(update, ctx, reply_markup=kb);   handled = True; break
        if text == T[lang].get("btn_week"):
            await summary_week(update, ctx, reply_markup=kb);  handled = True; break
        if text == T[lang].get("btn_month"):
            await summary_month(update, ctx, reply_markup=kb); handled = True; break
        if text == T[lang].get("btn_compare"):
            await compare_months(update, ctx, reply_markup=kb);handled = True; break
        if text == T[lang].get("btn_top_cat"):
            await top_categories(update, ctx, reply_markup=kb);handled = True; break
        if text == T[lang].get("btn_top_items"):
            await top_items(update, ctx, reply_markup=kb);     handled = True; break

    if handled:
        return REPORTS_MENU

    # Excel — show period selection and handle inline (can't delegate to another conv)
    if any(text == T[l].get("btn_export", "") for l in T):
        from keyboards import export_kb
        await update.message.reply_text(tr(uid, "export_period", s), reply_markup=export_kb(uid, s))
        ctx.user_data["in_export"] = True
        return REPORTS_MENU

    # Handle export period if we're in inline export mode
    if ctx.user_data.get("in_export"):
        import io
        from db import get_expenses, period_dates
        from excel import build_xlsx, XLSX_OK
        period_map = {
            tr(uid, "export_btn_today", s): "day",
            tr(uid, "export_btn_week",  s): "week",
            tr(uid, "export_btn_month", s): "month",
            tr(uid, "export_btn_all",   s): "all",
        }
        period = period_map.get(text)
        if period:
            ctx.user_data.pop("in_export", None)
            start, end = period_dates(period)
            rows = get_expenses(uid, start, end)
            if not rows:
                await update.message.reply_text(tr(uid, "export_empty", s), reply_markup=reports_kb(uid, s))
            elif not XLSX_OK:
                await update.message.reply_text(tr(uid, "export_no_xlsx", s), parse_mode="HTML", reply_markup=reports_kb(uid, s))
            else:
                await update.message.reply_text(tr(uid, "export_sending", s))
                data = build_xlsx(uid, rows, s)
                if data:
                    await update.message.reply_document(
                        document=io.BytesIO(data),
                        filename=f"expenses_{period}.xlsx",
                        reply_markup=reports_kb(uid, s),
                    )
                else:
                    await update.message.reply_text(tr(uid, "export_no_xlsx", s), reply_markup=reports_kb(uid, s))
            return REPORTS_MENU

    return REPORTS_MENU


def make_reports_conv() -> ConversationHandler:
    import re as _re
    texts  = [T[l]["btn_reports"] for l in T if T[l].get("btn_reports")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), reports_menu)],
        states={
            REPORTS_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, reports_action)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )


# ── More submenu ──────────────────────────────────────────────────────────────
async def more_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text("⚙️", reply_markup=more_kb(uid, s))
    return MORE_MENU


async def more_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = sanitize(update.message.text)

    if _is_back(text):
        await update.message.reply_text(tr(uid, "choose_menu", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END

    for lang in T:
        if text == T[lang].get("btn_help"):
            from handlers.settings import show_help
            await show_help(update, ctx)
            return MORE_MENU
        if text == T[lang].get("btn_feedback"):
            from handlers.feedback import feedback_start
            await feedback_start(update, ctx)
            return ConversationHandler.END
        if text == T[lang].get("btn_convert"):
            from handlers.converter import convert_start
            await convert_start(update, ctx)
            return ConversationHandler.END
        if text == T[lang].get("btn_limit"):
            from handlers.limits import limit_start
            await limit_start(update, ctx)
            return ConversationHandler.END
        if text == T[lang].get("btn_recurring"):
            from handlers.recurring import recur_start
            await recur_start(update, ctx)
            return ConversationHandler.END
        if text == T[lang].get("btn_reminders"):
            from handlers.reminders import remind_start
            await remind_start(update, ctx)
            return ConversationHandler.END
        if text == T[lang].get("btn_my_cats"):
            from handlers.categories import ccat_start
            await ccat_start(update, ctx)
            return ConversationHandler.END

    return MORE_MENU


def make_more_conv() -> ConversationHandler:
    import re as _re
    texts   = [T[l]["btn_more"] for l in T if T[l].get("btn_more")]
    pattern = "^(" + "|".join(_re.escape(t) for t in texts) + ")$"
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(pattern), more_menu)],
        states={
            MORE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, more_action)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        allow_reentry=True,
    )
