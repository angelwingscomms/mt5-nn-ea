"""Map feature names to shared macro names."""

from __future__ import annotations


def feature_macro_name(feature_name: str) -> str:
    if feature_name == "ret_n":
        return "RETURN_N"
    return feature_name.upper()
