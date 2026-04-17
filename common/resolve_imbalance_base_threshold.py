"""Resolve the non-EMA imbalance threshold."""

from __future__ import annotations


def resolve_imbalance_base_threshold(
    imbalance_min_ticks: int,
    *,
    use_imbalance_ema_threshold: bool,
    use_imbalance_min_ticks_div3_threshold: bool,
) -> float:
    if use_imbalance_ema_threshold or not use_imbalance_min_ticks_div3_threshold:
        return max(2.0, float(imbalance_min_ticks))
    return max(2.0, float(max(2, imbalance_min_ticks // 3)))
