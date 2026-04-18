from __future__ import annotations

from .shared import *  # noqa: F401,F403

def bool_literal(value: bool) -> str:
    return "true" if value else "false"
