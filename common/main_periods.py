"""Resolve the period tuple used by the notebook-style main feature set."""

from __future__ import annotations


def main_periods(values: dict) -> tuple[int, int, int, int, int]:
    return (
        int(values.get("FEATURE_MAIN_SHORT_PERIOD", 9)),
        int(values.get("FEATURE_MAIN_MEDIUM_PERIOD", 18)),
        int(values.get("FEATURE_MAIN_LONG_PERIOD", 27)),
        int(values.get("FEATURE_MAIN_XLONG_PERIOD", 54)),
        int(values.get("FEATURE_MAIN_XXLONG_PERIOD", 144)),
    )
