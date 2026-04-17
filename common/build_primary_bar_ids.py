"""Imbalance-bar id generation."""

from __future__ import annotations

import numpy as np

from common.resolve_imbalance_base_threshold import resolve_imbalance_base_threshold


def build_primary_bar_ids(
    tick_signs: np.ndarray,
    imbalance_min_ticks: int,
    imbalance_ema_span: int,
    use_imbalance_ema_threshold: bool,
    use_imbalance_min_ticks_div3_threshold: bool,
) -> np.ndarray:
    base_threshold = resolve_imbalance_base_threshold(
        imbalance_min_ticks,
        use_imbalance_ema_threshold=use_imbalance_ema_threshold,
        use_imbalance_min_ticks_div3_threshold=use_imbalance_min_ticks_div3_threshold,
    )
    expected_abs_theta = base_threshold
    bar_ids = np.empty(len(tick_signs), dtype=np.int64)
    current_bar = 0
    ticks_in_bar = 0
    theta = 0.0
    alpha = 2.0 / (max(1, imbalance_ema_span) + 1.0)

    for i, sign in enumerate(tick_signs):
        bar_ids[i] = current_bar
        ticks_in_bar += 1
        theta += float(sign)
        threshold = expected_abs_theta if use_imbalance_ema_threshold else base_threshold
        if ticks_in_bar >= imbalance_min_ticks and abs(theta) >= threshold:
            if use_imbalance_ema_threshold:
                observed = max(2.0, abs(theta))
                expected_abs_theta = (1.0 - alpha) * expected_abs_theta + alpha * observed
            current_bar += 1
            ticks_in_bar = 0
            theta = 0.0

    return bar_ids
