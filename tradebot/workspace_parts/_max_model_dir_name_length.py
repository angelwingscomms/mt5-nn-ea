from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _max_model_dir_name_length(symbol: str) -> int:
    """Return the longest archive folder name allowed by the MQL5 resource limit."""

    symbol_name = sanitize_symbol(symbol)
    fixed_length = len(f"symbols\\\\{symbol_name}\\\\models\\\\\\\\{MODEL_FILE_NAME}")
    max_length = RESOURCE_PATH_MAX_CHARS - fixed_length
    if max_length <= 0:
        raise ValueError(
            f"Resource path budget is exhausted for symbol '{symbol_name}'. "
            "Choose a shorter symbol folder name."
        )
    return max_length
