from __future__ import annotations

from .shared import *  # noqa: F401,F403

def set_line(name: str, value: str) -> str:
    return f"{name}={value}||{value}||0||{value}||N"
