from __future__ import annotations

from .shared import *  # noqa: F401,F403

def default_data_file(symbol: str) -> str:
    """Return the default CSV path for a symbol."""

    return f"data/{symbol.upper()}/ticks.csv"
