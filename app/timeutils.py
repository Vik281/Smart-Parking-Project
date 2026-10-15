"""All times are stored in the database as naive UTC datetimes.

Clients send timezone-aware times (e.g. "2026-10-15T09:30:00+05:30"); we convert
them to UTC on the way in and mark them as UTC on the way out. Keeping one rule
avoids the classic bug of comparing a local time with a UTC time.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_db_time(value: datetime) -> datetime:
    """Aware datetime (any timezone) -> naive UTC, ready to store or compare."""
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def from_db_time(value: datetime) -> datetime:
    """Naive UTC from the database -> aware UTC, so JSON responses end in 'Z'."""
    return value.replace(tzinfo=timezone.utc)
