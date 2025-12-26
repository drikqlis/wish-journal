import secrets
from datetime import datetime

from flask import session

YEAR_OFFSET = 942

MONTHS_POLISH = [
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "wrzesnia",
    "pazdziernika",
    "listopada",
    "grudnia",
]


def transform_date(dt: datetime | str) -> datetime:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    try:
        transformed = dt.replace(year=dt.year + YEAR_OFFSET)
    except ValueError:
        # Handle Feb 29 in non-leap years
        transformed = dt.replace(year=dt.year + YEAR_OFFSET, day=28)

    return transformed


def format_date_polish(dt: datetime | str, include_time: bool = False) -> str:
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return str(dt)

    transformed = transform_date(dt)
    date_str = f"{transformed.day} {MONTHS_POLISH[transformed.month - 1]} {transformed.year}"
    if include_time:
        date_str += f", {transformed.hour:02d}:{transformed.minute:02d}"
    return date_str


def generate_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validate_csrf_token(token: str | None) -> bool:
    return secrets.compare_digest(token or "", session.get("csrf_token", ""))
