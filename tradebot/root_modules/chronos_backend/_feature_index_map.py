from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _feature_index_map(feature_columns: Sequence[str]) -> dict[str, int]:
    index_map = {name: idx for idx, name in enumerate(feature_columns)}
    missing = [name for name in CHRONOS_BOLT_REQUIRED_FEATURES if name not in index_map]
    if missing:
        raise ValueError(f"Chronos-Bolt backend requires features {CHRONOS_BOLT_REQUIRED_FEATURES}, missing {missing}")
    return index_map
