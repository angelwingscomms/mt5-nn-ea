from __future__ import annotations

from .shared import *  # noqa: F401,F403

def current_log_stamp() -> str:
    return datetime.now().strftime("%Y%m%d")
