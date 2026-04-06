"""
handlers/core.py — core bot handlers:
  /start, onboarding, add expense, reports, top categories/items,
  delete last, donate.
"""
import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, filters,
)

from config import (
    CHOOSE_CATEGORY, ENTER_AMOUNT, ENTER_NAME,
    ONBOARD_LANG, ONBOARD_CUR_PRI, ONBOARD_CUR_SEC,
    DONATE_URL, LANG_BUTTONS, CURRENCY_BUTTONS,
)
from db import (
    get_settings, save_settings, is_first_time,
    add_expense, delete_last_expense,
    get_expenses, period_dates,
    get_limit, get_month_spent,
)
from i18n import tr, sym, cat_label, cat_key_from_label, detect_lang, fmt_date, month_name
from keyboards import main_kb, cat_kb, cancel_kb, lang_kb, curr_kb
from currency import get_rates, convert_amount, secondary_str
from security import is_allowed, sanitize, parse_amount

log = logging.getLogger(__name__)


# ── /start + onboarding ───────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    if is_first_time(uid):
        lang = detect_lang(update.effective_user.language_code)
        save_settings(uid, language=lang)
        s = get_settings(uid)
        await update.message.reply_text(
            tr(uid, "onboard_welcome", s), parse_mode="HTML",
            reply_markup=lang_kb(uid, s)
        )
        return ONBOARD_LANG
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "welcome", s), parse_mode="HTML", reply_markup=main_kb(uid, s)
    )
    return ConversationHandler.END


async def onboard_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = update.message.text.strip()
    lang_map = {v: k for k, v in LANG_BUTTONS.items()}
    if text in lang_map:
        save_settings(uid, language=lang_map[text])
        s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "onboard_cur_pri", s), parse_mode="HTML",
        reply_markup=curr_kb(uid, s, with_none=False)
    )
    return ONBOARD_CUR_PRI


async def onboard_cur_pri(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = update.message.text.strip()
    cur_map = {v: k for k, v in CURRENCY_BUTTONS.items()}
    if text in cur_map:
        save_settings(uid, primary_currency=cur_map[text])
        s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "onboard_cur_sec", s), parse_mode="HTML",
        reply_markup=curr_kb(uid, s, with_none=True)
    )
    return ONBOARD_CUR_SEC


async def onboard_cur_sec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    text = update.message.text.strip()
    cur_map = {v: k for k, v in CURRENCY_BUTTONS.items()}
    if text in cur_map:
        save_settings(uid, secondary_currency=cur_map[text])
    elif text == tr(uid, "curr_none", s):
        save_settings(uid, secondary_currency=None)
    s = get_settings(uid)
    await update.message.reply_text(
        tr(uid, "onboard_done", s), parse_mode="HTML",
        reply_markup=main_kb(uid, s)
    )
    return ConversationHandler.END


def make_start_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            ONBOARD_LANG:    [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_lang)],
            ONBOARD_CUR_PRI: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_cur_pri)],
            ONBOARD_CUR_SEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_cur_sec)],
        },
        fallbacks=[CommandHandler("start", cmd_start)],
        allow_reentry=True,
    )


# ── Donate ────────────────────────────────────────────────────────────────────
async def cmd_donate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s   = get_settings(uid)
    if not DONATE_URL:
        await update.message.reply_text(tr(uid, "donate_no_url", s), reply_markup=main_kb(uid, s))
        return
    await update.message.reply_text(
        tr(uid, "donate_msg", s, url=DONATE_URL),
        parse_mode="HTML", reply_markup=main_kb(uid, s),
        disable_web_page_preview=True,
    )


# ── Add expense ───────────────────────────────────────────────────────────────
async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return ConversationHandler.END
    s = get_settings(uid)
    await update.message.reply_text(tr(uid, "choose_cat", s), reply_markup=cat_kb(uid, s))
    return CHOOSE_CATEGORY


async def add_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    s     = get_settings(uid)
    label = sanitize(update.message.text)
    if label == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    key = cat_key_from_label(label, s["language"], uid)
    if not key:
        await update.message.reply_text(tr(uid, "choose_cat", s), reply_markup=cat_kb(uid, s))
        return CHOOSE_CATEGORY
    ctx.user_data["add_cat"]       = key
    ctx.user_data["add_cat_label"] = label
    await update.message.reply_text(
        tr(uid, "enter_amount", s, cat=label, sym=sym(s)),
        parse_mode="HTML", reply_markup=cancel_kb(uid, s),
    )
    return ENTER_AMOUNT


async def add_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    s      = get_settings(uid)
    text   = sanitize(update.message.text)
    if text == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    amount = parse_amount(text)
    if not amount:
        await update.message.reply_text(tr(uid, "bad_amount", s), reply_markup=cancel_kb(uid, s))
        return ENTER_AMOUNT
    ctx.user_data["add_amt"] = amount
    await update.message.reply_text(tr(uid, "enter_name", s), reply_markup=cancel_kb(uid, s))
    return ENTER_NAME


async def add_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid       = update.effective_user.id
    s         = get_settings(uid)
    name      = sanitize(update.message.text, 80)
    if name == tr(uid, "btn_cancel", s):
        await update.message.reply_text(tr(uid, "cancelled", s), reply_markup=main_kb(uid, s))
        return ConversationHandler.END
    cat       = ctx.user_data["add_cat"]
    cat_label_str = ctx.user_data["add_cat_label"]
    amount    = ctx.user_data["add_amt"]
    add_expense(uid, amount, cat, name)

    # Limit warning
    limit = get_limit(uid, cat)
    extra = ""
    if limit:
        spent = get_month_spent(uid, cat)
        if spent >= limit:
            extra = "\n" + tr(uid, "limit_over", s, cat=cat_label_str, spent=spent, limit=limit, sym=sym(s))
        elif spent >= limit * 0.8:
            extra = "\n" + tr(uid, "limit_warn", s, cat=cat_label_str, spent=spent, limit=limit,
                              pct=spent / limit * 100, sym=sym(s))

    # Secondary currency
    rates  = await get_rates()
    sec_s  = secondary_str(amount, s, rates)
    conv   = f"\n  ≈ {sec_s}" if sec_s else ""

    await update.message.reply_text(
        tr(uid, "saved", s, name=name, amount=amount, sym=sym(s), cat=cat_label_str) + conv + extra,
        parse_mode="HTML", reply_markup=main_kb(uid, s),
    )
    return ConversationHandler.END


def make_add_conv() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕"), add_start)],
        states={
            CHOOSE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
            ENTER_AMOUNT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount)],
            ENTER_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        },
        fallbacks=[CommandHandler("start", cmd_start), CommandHandler("cancel", cmd_start)],
        allow_reentry=True,
    )


# ── Delete last ───────────────────────────────────────────────────────────────
async def delete_last(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_allowed(uid):
        return
    s   = get_settings(uid)
    row = delete_last_expense(uid)
    if not row:
        await update.message.reply_text(tr(uid, "nothing_del", s), reply_markup=main_kb(uid, s))
        return
    cl = cat_label(s["language"], row["category"], uid)
    await update.message.reply_text(
        tr(uid, "deleted", s, name=row["item_name"], amount=float(row["amount"]),
           sym=sym(s), cat=cl),
        parse_mode="HTML", reply_markup=main_kb(uid, s),
    )


# ── Reports ───────────────────────────────────────────────────────────────────
def _progress_bar(pct: float, width: int = 8) -> str:
    filled = min(int(pct / 100 * width), width)
    return "█" * filled + "░" * (width - filled)


async def _format_and_send(update, uid: int, period: str, title_key: str,
                            reply_markup=None):
    s      = get_settings(uid)
    lang   = s["language"]
    _sym   = sym(s)
    start, end = period_dates(period)
    rows   = get_expenses(uid, start, end)

    if not rows:
        await update.message.reply_text(
            tr(uid, "no_data", s),
            reply_markup=reply_markup or main_kb(uid, s),
        )
        return

    rates = await get_rates()
    total = sum(float(r["amount"]) for r in rows)
    sec   = secondary_str(total, s, rates)

    by_day: dict[str, list] = defaultdict(list)
    for r in rows:
        by_day[str(r["created"])[:10]].append(r)

    lines = [f"<b>{tr(uid, title_key, s)}</b>"]

    if period in ("week", "month"):
        for day_str in sorted(by_day):
            dt       = datetime.strptime(day_str, "%Y-%m-%d")
            day_rows = by_day[day_str]
            day_tot  = sum(float(r["amount"]) for r in day_rows)
            lines.append(f"\n📆 <b>{fmt_date(day_str, lang)}</b> — {day_tot:.2f} {_sym}")
            for r in day_rows:
                cl = cat_label(lang, r["category"], uid)
                lines.append(f"  • {r['item_name']} [{cl}] — {float(r['amount']):.2f} {_sym}")
    else:
        for r in rows:
            cl = cat_label(lang, r["category"], uid)
            lines.append(f"  • {r['item_name']} [{cl}] — {float(r['amount']):.2f} {_sym}")

    lines.append(f"\n<b>{tr(uid, 'total_label', s)}: {total:.2f} {_sym}</b>")
    if sec:
        lines.append(f"≈ {sec}")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=reply_markup or main_kb(uid, s),
    )


async def summary_day(update, ctx, reply_markup=None):
    await _format_and_send(update, update.effective_user.id, "day", "title_today", reply_markup)

async def summary_week(update, ctx, reply_markup=None):
    await _format_and_send(update, update.effective_user.id, "week", "title_week", reply_markup)

async def summary_month(update, ctx, reply_markup=None):
    await _format_and_send(update, update.effective_user.id, "month", "title_month", reply_markup)


# ── Top categories / items ────────────────────────────────────────────────────
async def top_categories(update: Update, ctx: ContextTypes.DEFAULT_TYPE, reply_markup=None):
    uid = update.effective_user.id
    s   = get_settings(uid)
    start, end = period_dates("month")
    rows = get_expenses(uid, start, end)
    if not rows:
        await update.message.reply_text(
            tr(uid, "no_data", s), reply_markup=reply_markup or main_kb(uid, s)
        )
        return
    lang  = s["language"]
    _sym  = sym(s)
    rates = await get_rates()

    by_cat: dict[str, float] = defaultdict(float)
    for r in rows:
        by_cat[r["category"]] += float(r["amount"])
    total = sum(by_cat.values())
    sec   = secondary_str(total, s, rates)

    lines = [tr(uid, "title_top_cat", s), f"{tr(uid, 'total_label', s)}: {total:.2f} {_sym}"]
    if sec:
        lines.append(f"≈ {sec}")
    for i, (k, v) in enumerate(sorted(by_cat.items(), key=lambda x: -x[1]), 1):
        pct = v / total * 100
        lines.append(f"{i}. {cat_label(lang, k, uid)}: {v:.2f} {_sym} {_progress_bar(pct)} {pct:.0f}%")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=reply_markup or main_kb(uid, s),
    )


async def top_items(update: Update, ctx: ContextTypes.DEFAULT_TYPE, reply_markup=None):
    uid = update.effective_user.id
    s   = get_settings(uid)
    start, end = period_dates("month")
    rows = get_expenses(uid, start, end)
    if not rows:
        await update.message.reply_text(
            tr(uid, "no_data", s), reply_markup=reply_markup or main_kb(uid, s)
        )
        return
    lang = s["language"]
    _sym = sym(s)

    by_item: dict[str, list] = defaultdict(lambda: [0.0, 0])
    for r in rows:
        by_item[r["item_name"]][0] += float(r["amount"])
        by_item[r["item_name"]][1] += 1

    lines = [tr(uid, "title_top_items", s)]
    for i, (name, (amt, cnt)) in enumerate(
            sorted(by_item.items(), key=lambda x: -x[1][0])[:10], 1):
        lines.append(f"{i}. {name} — {amt:.2f} {_sym} ({cnt} {tr(uid, 'times', s)})")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=reply_markup or main_kb(uid, s),
    )


# ── Compare months ────────────────────────────────────────────────────────────
async def compare_months(update: Update, ctx: ContextTypes.DEFAULT_TYPE, reply_markup=None):
    uid  = update.effective_user.id
    s    = get_settings(uid)
    lang = s["language"]
    _sym = sym(s)
    fmt  = "%Y-%m-%d %H:%M:%S"
    now  = datetime.now()

    cur_start  = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_end   = cur_start - timedelta(seconds=1)
    prev_start = prev_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    cur_rows  = get_expenses(uid, cur_start.strftime(fmt), now.strftime(fmt))
    prev_rows = get_expenses(uid, prev_start.strftime(fmt), prev_end.strftime(fmt))
    cur_total  = sum(float(r["amount"]) for r in cur_rows)
    prev_total = sum(float(r["amount"]) for r in prev_rows)

    if not cur_rows and not prev_rows:
        await update.message.reply_text(
            tr(uid, "compare_no_data", s), reply_markup=reply_markup or main_kb(uid, s)
        )
        return

    cur_m  = month_name(now.month, now.year, lang)
    prev_m = month_name(prev_end.month, prev_end.year, lang)

    lines = [tr(uid, "compare_title", s), ""]
    lines.append(f"<b>{tr(uid, 'compare_this', s)} ({cur_m})</b>: {cur_total:.2f} {_sym}")
    lines.append(f"<b>{tr(uid, 'compare_prev', s)} ({prev_m})</b>: {prev_total:.2f} {_sym}")
    lines.append("")

    if prev_total > 0:
        diff = cur_total - prev_total
        pct  = abs(diff) / prev_total * 100
        if diff > 0:
            lines.append(tr(uid, "compare_diff_more", s, diff=diff, pct=pct, sym=_sym))
        elif diff < 0:
            lines.append(tr(uid, "compare_diff_less", s, diff=abs(diff), pct=pct, sym=_sym))
        else:
            lines.append(tr(uid, "compare_diff_same", s))
    elif cur_total > 0:
        lines.append(tr(uid, "compare_diff_more", s, diff=cur_total, pct=100, sym=_sym))

    # By category
    cur_cat: dict[str, float]  = defaultdict(float)
    prev_cat: dict[str, float] = defaultdict(float)
    all_cats: set = set()
    for r in cur_rows:
        cur_cat[r["category"]]  += float(r["amount"]); all_cats.add(r["category"])
    for r in prev_rows:
        prev_cat[r["category"]] += float(r["amount"]); all_cats.add(r["category"])

    if all_cats:
        lines.append("")
        lines.append(f"<b>{tr(uid, 'compare_by_cat', s)}</b>")
        for cat in sorted(all_cats, key=lambda c: -(cur_cat.get(c, 0) + prev_cat.get(c, 0))):
            cl  = cat_label(lang, cat, uid)
            c_v = cur_cat.get(cat, 0)
            p_v = prev_cat.get(cat, 0)
            arrow = "▲" if c_v > p_v else ("▼" if c_v < p_v else "◆")
            lines.append(f"  {arrow} {cl}: {c_v:.2f} vs {p_v:.2f} {_sym}")

    await update.message.reply_text(
        "\n".join(lines), parse_mode="HTML",
        reply_markup=reply_markup or main_kb(uid, s),
    )
