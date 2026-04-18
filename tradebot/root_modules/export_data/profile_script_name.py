from __future__ import annotations

from .shared import *  # noqa: F401,F403

def profile_script_name(profile: str) -> str:
    return "data_gold" if profile == "gold" else "data"
