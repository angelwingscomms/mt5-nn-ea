"""Maximum feature lookback across one feature pack."""

from __future__ import annotations

from common.lookback_requirement import lookback_requirement


def max_feature_lookback(values: dict, feature_columns: tuple[str, ...]) -> int:
    return max(lookback_requirement(values, feature_name) for feature_name in feature_columns)
