from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_config_dir(symbol: str) -> Path:
    """Return the preset-config root for one symbol."""

    return symbol_dir(symbol) / "config"
