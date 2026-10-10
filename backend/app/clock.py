"""Single source of "now" so dev time travel and tests can shift it."""
from datetime import datetime, timedelta, timezone

_offset = timedelta(0)


def now() -> datetime:
    return datetime.now(timezone.utc) + _offset


def travel(delta: timedelta) -> datetime:
    global _offset
    _offset += delta
    return now()


def reset() -> None:
    global _offset
    _offset = timedelta(0)
