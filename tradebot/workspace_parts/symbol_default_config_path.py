from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_default_config_path(symbol: str) -> Path:
    """Return the symbol's default reusable config preset."""

    return symbol_config_dir(symbol) / "config.mqh"
