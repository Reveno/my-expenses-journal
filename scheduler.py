"""
scheduler.py — PTB JobQueue jobs for recurring expenses and reminders.
"""
import datetime
import calendar
import logging
from db import (get_all_recurring, add_expense, get_settings,
                get_users_with_reminders, get_last_expense_date)
from i18n import tr, sym

log = logging.getLogger(__name__)


async def job_recurring(context):
    """Runs daily at midnight UTC. Auto-inserts recurring expenses."""
    today = datetime.date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]

    for rec in get_all_recurring():
        # Fire on configured day, or last day of month if month is shorter
        effective_day = min(rec["day_of_month"], last_day)
        if effective_day != today.day:
            continue
        uid = rec["user_id"]
        s   = get_settings(uid)
        add_expense(uid, float(rec["amount"]), rec["category"], rec["name"])
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=tr(uid, "recur_auto", s, name=rec["name"],
                        amount=float(rec["amount"]), sym=sym(s)),
                parse_mode="HTML",
            )
        except Exception as e:
            log.warning("Could not notify uid=%s for recurring: %s", uid, e)


async def job_reminders(context):
    """Runs every 5 minutes. Sends reminders based on per-user settings (UTC)."""
    now     = datetime.datetime.utcnow()
    hhmm    = now.strftime("%H:%M")
    weekday = now.weekday()  # 0=Mon … 6=Sun

    for rs in get_users_with_reminders():
        uid = rs["user_id"]
        s   = get_settings(uid)

        # Inactivity reminder — sent once daily at 09:00 UTC
        if rs["inactive_days"] > 0 and hhmm == "09:00":
            last = get_last_expense_date(uid)
            if last:
                last_date = datetime.datetime.strptime(last[:10], "%Y-%m-%d").date()
                inactive  = (datetime.date.today() - last_date).days
                if inactive >= rs["inactive_days"]:
                    try:
                        await context.bot.send_message(
                            chat_id=uid, parse_mode="HTML",
                            text=tr(uid, "remind_inact_msg", s, days=inactive),
                        )
                    except Exception as e:
                        log.warning("Inactivity reminder failed uid=%s: %s", uid, e)

        # Daily digest
        if rs.get("daily_time") and rs["daily_time"] == hhmm:
            try:
                await context.bot.send_message(
                    chat_id=uid, parse_mode="HTML",
                    text=tr(uid, "remind_daily_msg", s, btn=tr(uid, "btn_today", s)),
                )
            except Exception as e:
                log.warning("Daily reminder failed uid=%s: %s", uid, e)

        # Weekly digest
        if (rs.get("weekly_day") is not None
                and rs.get("weekly_time")
                and rs["weekly_day"] == weekday
                and rs["weekly_time"] == hhmm):
            try:
                await context.bot.send_message(
                    chat_id=uid, parse_mode="HTML",
                    text=tr(uid, "remind_weekly_msg", s, btn=tr(uid, "btn_week", s)),
                )
            except Exception as e:
                log.warning("Weekly reminder failed uid=%s: %s", uid, e)


def setup_scheduler(app):
    """Register recurring and reminder jobs with PTB JobQueue."""
    app.job_queue.run_daily(
        job_recurring,
        time=datetime.time(0, 0, 0),
        name="recurring",
    )
    app.job_queue.run_repeating(
        job_reminders,
        interval=300,
        first=30,
        name="reminders",
    )
