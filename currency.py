"""
currency.py — fetches exchange rates from open.er-api.com (no API key needed).
Rates are cached in memory for 1 hour.
"""
import time
import json
import urllib.request
from config import CURRENCY_SYMBOLS

_cache: dict = {}
_cache_ts: float = 0.0
_TTL = 3600  # 1 hour


async def get_rates() -> dict:
    """Return USD-based rate dict, refreshing from API if cache expired."""
    global _cache, _cache_ts
    if _cache and (time.time() - _cache_ts) < _TTL:
        return _cache
    try:
        with urllib.request.urlopen("https://open.er-api.com/v6/latest/USD", timeout=5) as r:
            data = json.loads(r.read())
        if data.get("result") == "success":
            _cache    = data["rates"]
            _cache_ts = time.time()
    except Exception:
        pass  # return stale cache or empty dict
    return _cache


def convert_amount(amount, from_cur: str, to_cur: str, rates: dict) -> float | None:
    """Convert amount between currencies using USD as base. Returns None if unavailable."""
    if from_cur not in rates or to_cur not in rates:
        return None
    return float(amount) * rates[to_cur] / rates[from_cur]


def secondary_str(amount, s: dict, rates: dict) -> str:
    """Return '(~$12.34)' string for secondary currency, or empty string."""
    sec = s.get("secondary_currency")
    pri = s.get("primary_currency", "UAH")
    if not sec or sec == pri or not rates:
        return ""
    result = convert_amount(float(amount), pri, sec, rates)
    if result is None:
        return ""
    sym = CURRENCY_SYMBOLS.get(sec, sec)
    return f"(~{sym}{result:.2f})"
