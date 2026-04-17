from __future__ import annotations

from .shared import *  # noqa: F401,F403

def sanitize_symbol(symbol: str) -> str:
    """Return a filesystem-safe, lower-case symbol directory name."""

    cleaned = SAFE_SYMBOL_PATTERN.sub("_", symbol.strip())
    return (cleaned or "unknown").lower()
