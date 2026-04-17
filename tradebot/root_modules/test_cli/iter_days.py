from __future__ import annotations

from .shared import *  # noqa: F401,F403

def iter_days(month_start: date, month_end: date) -> list[date]:
    days: list[date] = []
    current = month_start
    while current < month_end:
        days.append(current)
        current += timedelta(days=1)
    return days
