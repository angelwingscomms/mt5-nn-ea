from __future__ import annotations

from .shared import *  # noqa: F401,F403

def ini_leverage_value(value: str) -> str:
    text = str(value).strip()
    if ":" in text:
        text = text.split(":", 1)[1].strip()
    return text or "200"
