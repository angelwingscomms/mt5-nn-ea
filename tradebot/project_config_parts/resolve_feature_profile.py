from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_feature_profile(values: dict[str, Scalar], feature_columns: tuple[str, ...]) -> str:
    """Return a short human-readable label for diagnostics and reports."""

    if bool(values.get("USE_MAIN_FEATURE_SET", False)):
        return "main"
    if bool(values.get("USE_MINIMAL_FEATURE_SET", False)):
        return "minimal"
    enabled_gold = any(name in feature_columns for name in GOLD_CONTEXT_FEATURE_COLUMNS)
    enabled_extra = any(name in feature_columns for name in EXTRA_FEATURE_COLUMNS)
    if enabled_gold and enabled_extra:
        return "full"
    if enabled_extra:
        return "custom-extra"
    if enabled_gold:
        return "gold-context"
    return "minimal-plus-required"
