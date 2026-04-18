"""Map feature names to config switch macros."""

from __future__ import annotations

from common.feature_macro_name import feature_macro_name


def feature_switch_name(feature_name: str) -> str:
    return f"FEATURE_{feature_macro_name(feature_name)}"
