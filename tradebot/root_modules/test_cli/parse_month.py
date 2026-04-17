from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_month(value: str | None) -> tuple[date, date]:
    if value:
        month_start = datetime.strptime(value, "%Y-%m").date().replace(day=1)
    else:
        today = date.today().replace(day=1)
        previous_month_last_day = today - timedelta(days=1)
        month_start = previous_month_last_day.replace(day=1)
    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)
    return month_start, month_end
