# My Expenses Journal Bot

Telegram bot for personal expense and income tracking. Supports 4 languages (uk/ru/en/de).

## Project structure

```
config.py       — constants, env vars, conversation states
db.py           — database layer (PostgreSQL on Railway, SQLite locally)
i18n.py         — translations loaded from locales/*.json
currency.py     — exchange rates (open.er-api.com, cached 1h)
security.py     — input sanitisation and user whitelist
keyboards.py    — all keyboard builders
excel.py        — Excel report (3 sheets)
scheduler.py    — recurring expenses + reminder jobs
main.py         — entry point
handlers/
  core.py       — /start, onboarding, add expense, reports
  menus.py      — Finance / Reports / More submenus
  templates.py  — quick templates
  settings.py   — language, currency, help, donate
  limits.py     — spending limits
  categories.py — custom categories
  converter.py  — currency converter
  export.py     — Excel export
  recurring.py  — recurring expenses
  reminders.py  — reminder settings
  feedback.py   — user feedback + admin /reply
locales/        — uk.json, ru.json, en.json, de.json
```

## Local setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN and ADMIN_ID
python main.py
```

SQLite is used automatically when DATABASE_URL is not set.

## Deploy on Railway

1. Push to GitHub (`.env` is excluded by `.gitignore`)
2. Railway → New Project → Deploy from GitHub
3. Add PostgreSQL plugin (`DATABASE_URL` is set automatically)
4. Add variables: `BOT_TOKEN`, `ADMIN_ID`, `DONATE_URL`

## Environment variables

| Variable       | Required | Description                                  |
|----------------|----------|----------------------------------------------|
| `BOT_TOKEN`    | ✅       | Token from @BotFather                        |
| `DATABASE_URL` | —        | PostgreSQL URL (Railway sets this auto)      |
| `ADMIN_ID`     | —        | Your Telegram ID for receiving feedback      |
| `DONATE_URL`   | —        | Donation link (PayPal, Monobank, etc.)       |
| `ALLOWED_USERS`| —        | Comma-separated whitelist (empty = public)   |

## Admin commands

- `/reply USER_ID text` — reply to a feedback message
