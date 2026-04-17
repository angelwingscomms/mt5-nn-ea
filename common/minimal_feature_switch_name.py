"""Map minimal feature names to config switch macros."""

from __future__ import annotations

from common.feature_macro_name import feature_macro_name


def minimal_feature_switch_name(feature_name: str) -> str:
    return f"MINIMAL_FEATURE_{feature_macro_name(feature_name)}"
