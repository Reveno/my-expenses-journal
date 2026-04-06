"""
keyboards.py — ReplyKeyboardMarkup builders for every screen.
"""
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from config import BUILT_IN_KEYS, CATEGORY_LABELS, CURRENCY_BUTTONS, LANG_BUTTONS
from i18n import tr, sym


def main_kb(uid: int, s: dict | None = None) -> ReplyKeyboardMarkup:
    g = lambda k: tr(uid, k, s)
    return ReplyKeyboardMarkup([
        [g("btn_add"),      g("btn_quick")],
        [g("btn_finance"),  g("btn_reports")],
        [g("btn_more"),     g("btn_settings")],
    ], resize_keyboard=True)


def finance_kb(uid: int, s: dict | None = None) -> ReplyKeyboardMarkup:
    g = lambda k: tr(uid, k, s)
    return ReplyKeyboardMarkup([
        [g("btn_add_income_short")],
        [g("btn_back")],
    ], resize_keyboard=True)


def reports_kb(uid: int, s: dict | None = None) -> ReplyKeyboardMarkup:
    g = lambda k: tr(uid, k, s)
    return ReplyKeyboardMarkup([
        [g("btn_today"),    g("btn_week")],
        [g("btn_month"),    g("btn_compare")],
        [g("btn_top_cat"),  g("btn_top_items")],
        [g("btn_export")],
        [g("btn_back")],
    ], resize_keyboard=True)


def more_kb(uid: int, s: dict | None = None) -> ReplyKeyboardMarkup:
    g = lambda k: tr(uid, k, s)
    return ReplyKeyboardMarkup([
        [g("btn_limit"),    g("btn_recurring")],
        [g("btn_reminders"),g("btn_convert")],
        [g("btn_my_cats"),  g("btn_help")],
        [g("btn_feedback")],
        [g("btn_back")],
    ], resize_keyboard=True)


def cat_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    from db import get_custom_cats
    lang = s.get("language", "uk")
    labels = CATEGORY_LABELS.get(lang, CATEGORY_LABELS["uk"])
    rows = [[labels[k]] for k in BUILT_IN_KEYS]
    for c in get_custom_cats(uid):
        rows.append([c["label"]])
    rows.append([tr(uid, "btn_cancel", s)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def cancel_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[tr(uid, "btn_cancel", s)]], resize_keyboard=True)


def lang_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[v] for v in LANG_BUTTONS.values()], resize_keyboard=True, one_time_keyboard=True
    )


def curr_kb(uid: int, s: dict, with_none: bool = False) -> ReplyKeyboardMarkup:
    rows = [[v] for v in CURRENCY_BUTTONS.values()]
    if with_none:
        rows.append([tr(uid, "curr_none", s)])
    rows.append([tr(uid, "btn_cancel", s)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def export_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    g = lambda k: tr(uid, k, s)
    return ReplyKeyboardMarkup([
        [g("export_btn_today"), g("export_btn_week")],
        [g("export_btn_month"), g("export_btn_all")],
        [g("btn_cancel")],
    ], resize_keyboard=True, one_time_keyboard=True)


def tmpl_kb(uid: int, s: dict, templates: list) -> ReplyKeyboardMarkup:
    rows = [[f"⚡ {t['name']} ({float(t['amount']):.0f} {sym(s)})"] for t in templates]
    rows.append([tr(uid, "btn_tmpl_add", s), tr(uid, "btn_tmpl_del", s)])
    rows.append([tr(uid, "btn_cancel", s)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def settings_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [tr(uid, "btn_lang", s),   tr(uid, "btn_currency", s)],
        [tr(uid, "btn_donate", s)],
        [tr(uid, "btn_cancel", s)],
    ], resize_keyboard=True, one_time_keyboard=True)


def recur_kb(uid: int, s: dict, items: list) -> ReplyKeyboardMarkup:
    _sym = sym(s)
    rows = [[f"🔁 {r['name']} — {float(r['amount']):.0f} {_sym} ({r['day_of_month']}-го)"]
            for r in items]
    rows.append([tr(uid, "btn_recur_add", s), tr(uid, "btn_recur_del", s)])
    rows.append([tr(uid, "btn_cancel", s)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def recur_del_kb(uid: int, s: dict, items: list) -> ReplyKeyboardMarkup:
    rows = [[f"🗑 {r['name']}"] for r in items]
    rows.append([tr(uid, "btn_cancel", s)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def remind_kb(uid: int, s: dict) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        [tr(uid, "remind_btn_inactive", s)],
        [tr(uid, "remind_btn_daily", s)],
        [tr(uid, "remind_btn_weekly", s)],
        [tr(uid, "btn_cancel", s)],
    ], resize_keyboard=True, one_time_keyboard=True)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
