from __future__ import annotations

from .shared import *  # noqa: F401,F403

def symbol_backtest_config_path(symbol: str) -> Path:
    """Return the symbol's default backtest JSON config."""

    return symbol_config_dir(symbol) / DEFAULT_TEST_CONFIG_NAME
