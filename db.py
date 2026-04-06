"""
db.py — database layer. Supports both PostgreSQL (Railway) and SQLite (local).
All SQL queries use ? placeholders; the DB wrappers handle dialect differences.
"""
import os
import sqlite3
import logging
import calendar
from datetime import datetime, timedelta
from config import DATABASE_URL, DB_PATH, USE_PG

# ── psycopg2 — optional, required only when USE_PG=True ──────────────────────
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False
    class _FakePg:
        def __getattr__(self, name):
            raise ImportError("psycopg2 is required. Run: pip install psycopg2-binary")
    psycopg2 = _FakePg()  # type: ignore


# ── DB wrappers ───────────────────────────────────────────────────────────────
class _PgDB:
    """Context-manager wrapper for psycopg2 (PostgreSQL)."""
    def __init__(self, conn):
        self._conn = conn
        self._cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)  # type: ignore

    def execute(self, sql: str, params=()):
        self._cur.execute(sql.replace("?", "%s"), params or ())
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._cur.close()
        self._conn.close()


class _SqliteDB:
    """Context-manager wrapper for sqlite3 (local development)."""
    def __init__(self, conn):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._cur = self._conn.cursor()

    def execute(self, sql: str, params=()):
        self._cur.execute(sql, params or ())
        return self._cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()


def get_db() -> _PgDB | _SqliteDB:
    if USE_PG:
        if not PSYCOPG2_OK:
            raise RuntimeError(
                "DATABASE_URL is set but psycopg2 is not installed!\n"
                "Add 'psycopg2-binary' to requirements.txt"
            )
        conn = psycopg2.connect(DATABASE_URL)  # type: ignore
        return _PgDB(conn)
    d = os.path.dirname(DB_PATH)
    if d:
        os.makedirs(d, exist_ok=True)
    return _SqliteDB(sqlite3.connect(DB_PATH))


def init_db():
    """Create all tables. PostgreSQL on Railway, SQLite locally."""
    if USE_PG:
        stmts = [
            """CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL,
                amount NUMERIC(12,2) NOT NULL, category TEXT NOT NULL,
                item_name TEXT NOT NULL, created TIMESTAMP NOT NULL DEFAULT NOW()
            )""",
            """CREATE TABLE IF NOT EXISTS limits (
                user_id BIGINT NOT NULL, category TEXT NOT NULL,
                amount NUMERIC(12,2) NOT NULL, PRIMARY KEY (user_id, category)
            )""",
            """CREATE TABLE IF NOT EXISTS user_settings (
                user_id BIGINT PRIMARY KEY, language TEXT NOT NULL DEFAULT 'uk',
                primary_currency TEXT NOT NULL DEFAULT 'UAH',
                secondary_currency TEXT DEFAULT 'USD'
            )""",
            """CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL,
                name TEXT NOT NULL, amount NUMERIC(12,2) NOT NULL, category TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS custom_categories (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, label TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS recurring (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL,
                name TEXT NOT NULL, amount NUMERIC(12,2) NOT NULL,
                category TEXT NOT NULL, day_of_month INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS reminder_settings (
                user_id BIGINT PRIMARY KEY, inactive_days INTEGER NOT NULL DEFAULT 0,
                daily_time TEXT DEFAULT NULL, weekly_day INTEGER DEFAULT NULL,
                weekly_time TEXT DEFAULT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS income (
                id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL,
                amount NUMERIC(12,2) NOT NULL, source TEXT NOT NULL,
                created TIMESTAMP NOT NULL DEFAULT NOW()
            )""",
        ]
        with get_db() as db:
            for s in stmts:
                db.execute(s)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                amount REAL NOT NULL, category TEXT NOT NULL,
                item_name TEXT NOT NULL,
                created TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS limits (
                user_id INTEGER NOT NULL, category TEXT NOT NULL, amount REAL NOT NULL,
                PRIMARY KEY (user_id, category)
            );
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY, language TEXT NOT NULL DEFAULT 'uk',
                primary_currency TEXT NOT NULL DEFAULT 'UAH',
                secondary_currency TEXT DEFAULT 'USD'
            );
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                name TEXT NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS custom_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, label TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recurring (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                name TEXT NOT NULL, amount REAL NOT NULL,
                category TEXT NOT NULL, day_of_month INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminder_settings (
                user_id INTEGER PRIMARY KEY,
                inactive_days INTEGER NOT NULL DEFAULT 0,
                daily_time TEXT DEFAULT NULL,
                weekly_day INTEGER DEFAULT NULL,
                weekly_time TEXT DEFAULT NULL
            );
            CREATE TABLE IF NOT EXISTS income (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                amount REAL NOT NULL, source TEXT NOT NULL,
                created TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );
        """)
        conn.commit()
        conn.close()
        logging.info("SQLite DB ready at %s", DB_PATH)


# ── Settings ──────────────────────────────────────────────────────────────────
_DEFAULT_SETTINGS = {"language": "uk", "primary_currency": "UAH", "secondary_currency": "USD"}


def get_settings(uid: int) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM user_settings WHERE user_id=?", (uid,)).fetchone()
    return dict(row) if row else dict(_DEFAULT_SETTINGS)


def is_first_time(uid: int) -> bool:
    with get_db() as db:
        return db.execute("SELECT 1 FROM user_settings WHERE user_id=?", (uid,)).fetchone() is None


def save_settings(uid: int, **kw):
    s = get_settings(uid)
    s.update(kw)
    with get_db() as db:
        db.execute(
            "INSERT INTO user_settings (user_id, language, primary_currency, secondary_currency) "
            "VALUES (?,?,?,?) ON CONFLICT (user_id) DO UPDATE SET "
            "language=EXCLUDED.language, primary_currency=EXCLUDED.primary_currency, "
            "secondary_currency=EXCLUDED.secondary_currency",
            (uid, s["language"], s["primary_currency"], s.get("secondary_currency")),
        )


# ── Expenses ──────────────────────────────────────────────────────────────────
def period_dates(period: str) -> tuple[str, str]:
    """Return (start, end) ISO datetime strings for given period."""
    now = datetime.now()
    fmt = "%Y-%m-%d %H:%M:%S"
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = datetime(2000, 1, 1)
    return start.strftime(fmt), now.strftime(fmt)


def get_expenses(uid: int, start: str, end: str) -> list:
    with get_db() as db:
        return db.execute(
            "SELECT * FROM expenses WHERE user_id=? AND created BETWEEN ? AND ? ORDER BY created",
            (uid, start, end),
        ).fetchall()


def add_expense(uid: int, amount: float, category: str, name: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, item_name) VALUES (?,?,?,?)",
            (uid, amount, category, name),
        )


def delete_last_expense(uid: int) -> dict | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM expenses WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
        ).fetchone()
        if not row:
            return None
        db.execute("DELETE FROM expenses WHERE id=?", (row["id"],))
    return dict(row)


def get_last_expense_date(uid: int) -> str | None:
    with get_db() as db:
        row = db.execute(
            "SELECT MAX(created) AS last FROM expenses WHERE user_id=?", (uid,)
        ).fetchone()
    v = row["last"] if row else None
    return str(v)[:19] if v else None


# ── Limits ────────────────────────────────────────────────────────────────────
def get_limit(uid: int, category: str) -> float | None:
    with get_db() as db:
        row = db.execute(
            "SELECT amount FROM limits WHERE user_id=? AND category=?", (uid, category)
        ).fetchone()
    return float(row["amount"]) if row else None


def set_limit(uid: int, category: str, amount: float):
    with get_db() as db:
        if amount == 0:
            db.execute("DELETE FROM limits WHERE user_id=? AND category=?", (uid, category))
        else:
            db.execute(
                "INSERT INTO limits (user_id, category, amount) VALUES (?,?,?) "
                "ON CONFLICT (user_id, category) DO UPDATE SET amount=EXCLUDED.amount",
                (uid, category, amount),
            )


def get_month_spent(uid: int, category: str) -> float:
    start, end = period_dates("month")
    with get_db() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS v FROM expenses "
            "WHERE user_id=? AND category=? AND created BETWEEN ? AND ?",
            (uid, category, start, end),
        ).fetchone()
    return float(row["v"]) if row else 0.0


# ── Custom categories ─────────────────────────────────────────────────────────
def get_custom_cats(uid: int) -> list[dict]:
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM custom_categories WHERE user_id=? ORDER BY label", (uid,)
        ).fetchall()]


def add_custom_cat(uid: int, label: str):
    with get_db() as db:
        db.execute("INSERT INTO custom_categories (user_id, label) VALUES (?,?)", (uid, label))


def del_custom_cat(cat_id: int):
    with get_db() as db:
        db.execute("DELETE FROM custom_categories WHERE id=?", (cat_id,))


# ── Templates ─────────────────────────────────────────────────────────────────
def get_templates(uid: int) -> list[dict]:
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM templates WHERE user_id=? ORDER BY name", (uid,)
        ).fetchall()]


def add_template(uid: int, name: str, amount: float, category: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO templates (user_id, name, amount, category) VALUES (?,?,?,?)",
            (uid, name, amount, category),
        )


def del_template(tmpl_id: int):
    with get_db() as db:
        db.execute("DELETE FROM templates WHERE id=?", (tmpl_id,))


# ── Recurring expenses ────────────────────────────────────────────────────────
def get_recurring(uid: int) -> list[dict]:
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM recurring WHERE user_id=? ORDER BY day_of_month, name", (uid,)
        ).fetchall()]


def get_all_recurring() -> list[dict]:
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM recurring").fetchall()]


def add_recurring(uid: int, name: str, amount: float, category: str, day: int):
    with get_db() as db:
        db.execute(
            "INSERT INTO recurring (user_id, name, amount, category, day_of_month) VALUES (?,?,?,?,?)",
            (uid, name, amount, category, day),
        )


def del_recurring(rec_id: int):
    with get_db() as db:
        db.execute("DELETE FROM recurring WHERE id=?", (rec_id,))


# ── Reminder settings ─────────────────────────────────────────────────────────
_DEFAULT_REMINDERS = {
    "inactive_days": 0, "daily_time": None, "weekly_day": None, "weekly_time": None
}


def get_reminder_settings(uid: int) -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM reminder_settings WHERE user_id=?", (uid,)).fetchone()
    return dict(row) if row else {"user_id": uid, **_DEFAULT_REMINDERS}


def save_reminder_settings(uid: int, **kw):
    rs = get_reminder_settings(uid)
    rs.update(kw)
    with get_db() as db:
        db.execute(
            "INSERT INTO reminder_settings "
            "(user_id, inactive_days, daily_time, weekly_day, weekly_time) VALUES (?,?,?,?,?) "
            "ON CONFLICT (user_id) DO UPDATE SET "
            "inactive_days=EXCLUDED.inactive_days, daily_time=EXCLUDED.daily_time, "
            "weekly_day=EXCLUDED.weekly_day, weekly_time=EXCLUDED.weekly_time",
            (uid, rs["inactive_days"], rs["daily_time"], rs["weekly_day"], rs["weekly_time"]),
        )


def get_users_with_reminders() -> list[dict]:
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM reminder_settings "
            "WHERE inactive_days > 0 OR daily_time IS NOT NULL OR weekly_day IS NOT NULL"
        ).fetchall()]


# ── Income ────────────────────────────────────────────────────────────────────
def add_income(uid: int, amount: float, source: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO income (user_id, amount, source) VALUES (?,?,?)",
            (uid, amount, source),
        )


def get_month_income(uid: int) -> float:
    start, end = period_dates("month")
    with get_db() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS v FROM income "
            "WHERE user_id=? AND created BETWEEN ? AND ?",
            (uid, start, end),
        ).fetchone()
    return float(row["v"]) if row else 0.0


def get_month_expenses_total(uid: int) -> float:
    start, end = period_dates("month")
    with get_db() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS v FROM expenses "
            "WHERE user_id=? AND created BETWEEN ? AND ?",
            (uid, start, end),
        ).fetchone()
    return float(row["v"]) if row else 0.0
