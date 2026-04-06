"""
security.py — user whitelist, input sanitisation, amount parsing.
"""
from config import ALLOWED_USERS, MAX_INPUT, MAX_AMOUNT


def is_allowed(uid: int) -> bool:
    """Returns True when bot is public (ALLOWED_USERS empty) or uid is whitelisted."""
    return not ALLOWED_USERS or uid in ALLOWED_USERS


def sanitize(text: str, max_len: int = MAX_INPUT) -> str:
    """Strip whitespace and truncate to max_len characters."""
    return (text or "").strip()[:max_len]


def parse_amount(text: str) -> float | None:
    """
    Parse user amount input. Returns float if valid and within limits, else None.
    Accepts both comma and dot as decimal separator.
    """
    try:
        v = float((text or "").replace(",", ".").replace(" ", ""))
        return v if 0 < v <= MAX_AMOUNT else None
    except ValueError:
        return None
