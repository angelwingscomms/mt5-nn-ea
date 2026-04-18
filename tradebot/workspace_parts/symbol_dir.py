from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_dir(symbol: str) -> Path:
    """Return the per-symbol workspace directory."""

    return SYMBOLS_DIR / sanitize_symbol(symbol)
