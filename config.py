"""
config.py — constants, environment variables, conversation states.
All other modules import from here.
"""
import os

# ── Environment ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # not needed on Railway

TOKEN = os.getenv("BOT_TOKEN", "")
if not TOKEN:
    print("\n" + "=" * 55)
    print("  ERROR: BOT_TOKEN not found!")
    print("  1. Run: pip install -r requirements.txt")
    print("  2. Make sure .env file exists next to bot.py")
    print("  3. .env must contain: BOT_TOKEN=your_token")
    print("=" * 55 + "\n")
    raise SystemExit(1)

DATABASE_URL  = os.getenv("DATABASE_URL", "")
DB_PATH       = os.getenv("DB_PATH", "expenses.db")
USE_PG        = bool(DATABASE_URL)
DONATE_URL    = os.getenv("DONATE_URL", "")

_raw_admin    = os.getenv("ADMIN_ID", "").strip()
ADMIN_ID: int = int(_raw_admin) if _raw_admin.isdigit() else 0

_raw_allow    = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS: frozenset[int] = frozenset(
    int(x) for x in _raw_allow.split(",") if x.strip().isdigit()
)

MAX_INPUT  = 100
MAX_AMOUNT = 999_999.99

# ── Currency display ──────────────────────────────────────────────────────────
CURRENCY_SYMBOLS = {"UAH": "₴", "USD": "$", "EUR": "€", "GBP": "£", "PLN": "zł"}
CURRENCY_BUTTONS = {
    "UAH": "₴ UAH — Гривня / Hryvnia",
    "USD": "$ USD — Долар / Dollar",
    "EUR": "€ EUR — Євро / Euro",
}
LANG_BUTTONS = {
    "uk": "🇺🇦 Українська",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
}
BUILT_IN_KEYS = [
    "food", "transport", "entertainment", "housing",
    "clothes", "health", "education", "pets", "other",
]
CATEGORY_LABELS = {
    "uk": {
        "food": "🍔 Їжа", "transport": "🚌 Транспорт",
        "entertainment": "🎮 Розваги", "housing": "🏠 Житло",
        "clothes": "👕 Одяг", "health": "💊 Здоров'я",
        "education": "📚 Освіта", "pets": "🐾 Тварини", "other": "🔧 Інше",
    },
    "ru": {
        "food": "🍔 Еда", "transport": "🚌 Транспорт",
        "entertainment": "🎮 Развлечения", "housing": "🏠 Жильё",
        "clothes": "👕 Одежда", "health": "💊 Здоровье",
        "education": "📚 Образование", "pets": "🐾 Питомцы", "other": "🔧 Другое",
    },
    "en": {
        "food": "🍔 Food", "transport": "🚌 Transport",
        "entertainment": "🎮 Entertainment", "housing": "🏠 Housing",
        "clothes": "👕 Clothes", "health": "💊 Health",
        "education": "📚 Education", "pets": "🐾 Pets", "other": "🔧 Other",
    },
    "de": {
        "food": "🍔 Essen", "transport": "🚌 Transport",
        "entertainment": "🎮 Freizeit", "housing": "🏠 Wohnen",
        "clothes": "👕 Kleidung", "health": "💊 Gesundheit",
        "education": "📚 Bildung", "pets": "🐾 Haustiere", "other": "🔧 Sonstiges",
    },
}

# ── Conversation states ───────────────────────────────────────────────────────
(
    CHOOSE_CATEGORY, ENTER_AMOUNT, ENTER_NAME,          # 0-2
    SET_LIMIT_CAT, SET_LIMIT_AMOUNT,                    # 3-4
    TMPL_ACTION, TMPL_ADD_NAME, TMPL_ADD_AMOUNT,        # 5-7
    TMPL_ADD_CAT, TMPL_DEL,                             # 8-9
    LANG_SELECT, CURR_PRIMARY, CURR_SECONDARY,          # 10-12
    CONVERT,                                            # 13
    EXPORT_PERIOD,                                      # 14
    CCAT_MENU, CCAT_NAME, CCAT_DEL,                    # 15-17
    RECUR_MENU, RECUR_NAME, RECUR_AMT,                 # 18-20
    RECUR_CAT, RECUR_DAY, RECUR_DEL,                   # 21-23
    REMIND_MENU, REMIND_INACT, REMIND_DAILY,            # 24-26
    REMIND_WDAY, REMIND_WTIME,                          # 27-28
    SETTINGS_MENU,                                      # 29
    ONBOARD_LANG, ONBOARD_CUR_PRI, ONBOARD_CUR_SEC,    # 30-32
    FEEDBACK_MSG,                                       # 33
    INCOME_AMT, INCOME_SRC,                             # 34-35
    FINANCE_MENU, REPORTS_MENU, MORE_MENU,              # 36-38
) = range(39)
