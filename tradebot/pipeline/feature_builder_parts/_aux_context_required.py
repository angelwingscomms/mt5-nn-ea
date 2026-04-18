from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _aux_context_required(feature_columns: tuple[str, ...]) -> bool:
    required_columns = GOLD_CONTEXT_FEATURE_COLUMNS + MAIN_GOLD_CONTEXT_FEATURE_COLUMNS
    return any(name in feature_columns for name in required_columns)
