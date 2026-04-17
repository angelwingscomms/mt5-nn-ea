from __future__ import annotations

from .shared import *  # noqa: F401,F403

def feature_macro_name(feature_name: str) -> str:
    return f"FEATURE_IDX_{project_feature_macro_name(feature_name)}"
