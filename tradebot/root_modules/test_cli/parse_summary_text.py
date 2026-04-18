from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_summary_text(text: str) -> dict[str, int | float | str]:
    match = SUMMARY_PATTERN.search(text)
    if not match:
        return {}
    values: dict[str, int | float | str] = {}
    for token in match.group(1).split():
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if NUMBER_PATTERN.match(value):
            numeric = float(value)
            values[key] = int(numeric) if numeric.is_integer() else numeric
        elif BOOL_PATTERN.match(value):
            values[key] = value.lower() == "true"
        else:
            values[key] = value
    return values
