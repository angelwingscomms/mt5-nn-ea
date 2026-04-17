"""Map feature names to MQL feature-index macros."""

from __future__ import annotations

from common.feature_macro_name import feature_macro_name


def feature_index_macro_name(feature_name: str) -> str:
    return f"FEATURE_IDX_{feature_macro_name(feature_name)}"
