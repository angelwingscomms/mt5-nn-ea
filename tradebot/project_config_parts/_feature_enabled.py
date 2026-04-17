from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _feature_enabled(values: dict[str, Scalar], feature_name: str) -> bool:
    return bool(values.get(feature_switch_name(feature_name), False))
