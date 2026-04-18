from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_single_day(value: str) -> date:
    text = value.strip()
    if not re.fullmatch(r"\d{6}", text):
        raise ValueError("Daily test dates must use DDMMYY format, for example 050426.")
    return datetime.strptime(text, "%d%m%y").date()
