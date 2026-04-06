"""
main.py — assembles all handlers and starts the bot.

Project structure:
  config.py       — constants, env vars, conversation states
  db.py           — database layer (PostgreSQL / SQLite)
  i18n.py         — translations loaded from locales/*.json
  currency.py     — exchange rates (open.er-api.com)
  security.py     — input validation and user whitelist
  keyboards.py    — all ReplyKeyboardMarkup builders
  excel.py        — Excel report generation
  scheduler.py    — recurring expenses + reminder jobs
  handlers/
    core.py       — /start, onboarding, add expense, reports, top, delete
    menus.py      — Finance / Reports / More submenu conversations
    templates.py  — quick templates (⚡)
    settings.py   — language, currency, help, donate
    limits.py     — spending limits
    categories.py — custom categories
    converter.py  — currency converter
    export.py     — Excel export
    recurring.py  — recurring expenses management
    reminders.py  — reminder settings
    feedback.py   — user feedback + admin /reply
  locales/        — uk.json, ru.json, en.json, de.json
"""
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, AIORateLimiter,
)

from config import TOKEN
from db import init_db
from scheduler import setup_scheduler

from handlers.core import (
    make_start_conv, make_add_conv, delete_last, cmd_donate,
)
from handlers.menus     import make_finance_conv, make_reports_conv, make_more_conv
from handlers.templates import make_tmpl_conv
from handlers.settings  import make_settings_conv
from handlers.limits    import make_limits_conv
from handlers.categories import make_ccat_conv
from handlers.converter import make_converter_conv
from handlers.export    import make_export_conv
from handlers.recurring import make_recur_conv
from handlers.reminders import make_reminders_conv
from handlers.feedback  import make_feedback_conv, cmd_reply

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def main():
    init_db()
    log.info("Database initialised")

    try:
        app = ApplicationBuilder().token(TOKEN).rate_limiter(AIORateLimiter()).build()
    except Exception:
        app = ApplicationBuilder().token(TOKEN).build()

    # ── Conversation handlers (order matters — first match wins) ──────────────
    for conv in [
        make_start_conv(),
        make_finance_conv(),
        make_reports_conv(),
        make_more_conv(),
        make_add_conv(),
        make_tmpl_conv(),
        make_settings_conv(),
        make_limits_conv(),
        make_ccat_conv(),
        make_converter_conv(),
        make_export_conv(),
        make_recur_conv(),
        make_reminders_conv(),
        make_feedback_conv(),
    ]:
        app.add_handler(conv)

    # ── Simple command handlers ───────────────────────────────────────────────
    app.add_handler(CommandHandler("donate", cmd_donate))
    app.add_handler(CommandHandler("reply",  cmd_reply))

    # ── Simple button handlers ────────────────────────────────────────────────
    from i18n import T

    def _pat(*keys: str) -> str:
        texts = {T[l][k] for l in T for k in keys if k in T[l]}
        import re
        return "^(" + "|".join(re.escape(t) for t in texts) + ")$"

    app.add_handler(MessageHandler(filters.Regex(_pat("btn_delete")), delete_last))

    # ── Scheduler ─────────────────────────────────────────────────────────────
    setup_scheduler(app)

    log.info("Bot started — polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
