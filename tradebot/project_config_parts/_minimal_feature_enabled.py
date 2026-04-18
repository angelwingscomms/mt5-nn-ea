from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _minimal_feature_enabled(values: dict[str, Scalar], feature_name: str) -> bool:
    return bool(values.get(minimal_feature_switch_name(feature_name), feature_name in MINIMAL_FEATURE_COLUMNS))
