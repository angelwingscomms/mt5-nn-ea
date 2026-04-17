from __future__ import annotations

from .shared import *  # noqa: F401,F403

def configured_symbol(config_path: Path = ACTIVE_CONFIG_PATH) -> str:
    """Read the active symbol from the user-editable root config."""

    values = load_define_file(config_path)
    return str(values.get("SYMBOL", "XAUUSD")).strip() or "XAUUSD"
