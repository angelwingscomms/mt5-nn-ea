from __future__ import annotations

from .shared import *  # noqa: F401,F403

def filter_days(days: list[date], from_date: str, to_date: str) -> list[date]:
    start = date.fromisoformat(from_date) if from_date else None
    end = date.fromisoformat(to_date) if to_date else None
    filtered: list[date] = []
    for day_value in days:
        if start and day_value < start:
            continue
        if end and day_value > end:
            continue
        filtered.append(day_value)
    return filtered
