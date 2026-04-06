"""
i18n.py — loads translations from locales/*.json and exposes tr(), sym(), etc.
"""
import json, calendar
from pathlib import Path
from config import CURRENCY_SYMBOLS, CATEGORY_LABELS, BUILT_IN_KEYS

_LOCALES_DIR = Path(__file__).parent / "locales"

# Load all locale files into T dict
T: dict[str, dict[str, str]] = {}
for _path in sorted(_LOCALES_DIR.glob("*.json")):
    lang = _path.stem
    with open(_path, encoding="utf-8") as _f:
        T[lang] = json.load(_f)

SUPPORTED_LANGS = list(T.keys())
TG_LANG_MAP = {
    "uk": "uk", "ru": "ru",
    "en": "en", "en-us": "en", "en-gb": "en",
    "de": "de", "de-de": "de", "de-at": "de", "de-ch": "de",
}


def detect_lang(code: str | None) -> str:
    """Detect bot language from Telegram language_code."""
    if not code:
        return "uk"
    c = code.lower()
    return TG_LANG_MAP.get(c, TG_LANG_MAP.get(c.split("-")[0], "uk"))


def tr(uid: int, key: str, s: dict | None = None, **kw) -> str:
    """Translate key for user uid using settings dict s."""
    from db import get_settings
    lang = (s or get_settings(uid)).get("language", "uk")
    text = T.get(lang, T["uk"]).get(key, T["uk"].get(key, key))
    return text.format(**kw) if kw else text


def sym(s: dict) -> str:
    """Return currency symbol for user's primary currency."""
    return CURRENCY_SYMBOLS.get(s.get("primary_currency", "UAH"), "₴")


def month_name(month: int, year: int, lang: str) -> str:
    """Return localized short month name using Python's calendar module."""
    _month_names = {
        "uk": ["", "Січ", "Лют", "Бер", "Кві", "Тра", "Чер",
               "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"],
        "ru": ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
        "en": ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "de": ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    }
    names = _month_names.get(lang, _month_names["en"])
    abbr = names[month] if 1 <= month <= 12 else calendar.month_abbr[month]
    return f"{abbr} {year}"


def last_day_of_month(year: int, month: int) -> int:
    """Return last day of month using calendar module."""
    return calendar.monthrange(year, month)[1]


def cat_label(lang: str, key: str, uid: int | None = None) -> str:
    """Return display label for category key."""
    if key.startswith("cust:") and uid is not None:
        from db import get_custom_cats
        cid = int(key.split(":")[1])
        for c in get_custom_cats(uid):
            if c["id"] == cid:
                return c["label"]
        return key
    return CATEGORY_LABELS.get(lang, CATEGORY_LABELS["uk"]).get(key, key)


def cat_key_from_label(label: str, lang: str, uid: int) -> str | None:
    """Return category key from display label."""
    for k, v in CATEGORY_LABELS.get(lang, {}).items():
        if v == label:
            return k
    from db import get_custom_cats
    for c in get_custom_cats(uid):
        if c["label"] == label:
            return f"cust:{c['id']}"
    return None


def fmt_date(date_str: str, lang: str) -> str:
    """Format date string as 'DD Mon'."""
    from datetime import datetime
    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
    names = {
        "uk": ["", "Січ", "Лют", "Бер", "Кві", "Тра", "Чер",
               "Лип", "Сер", "Вер", "Жов", "Лис", "Гру"],
        "ru": ["", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
               "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
        "en": ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "de": ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
    }
    return f"{dt.day:02d} {names.get(lang, names['en'])[dt.month]}"
