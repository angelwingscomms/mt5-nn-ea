from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_models_dir(symbol: str) -> Path:
    """Return the archived-model root for one symbol."""

    return symbol_dir(symbol) / "models"
