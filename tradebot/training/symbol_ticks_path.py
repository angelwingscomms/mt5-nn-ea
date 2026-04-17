from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_ticks_path(symbol: str) -> Path:
    return Path("data") / symbol.strip().upper() / "ticks.csv"
