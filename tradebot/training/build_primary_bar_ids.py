from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_primary_bar_ids(df_ticks: pd.DataFrame) -> np.ndarray:
    prices = df_ticks["bid"].to_numpy(dtype=np.float64, copy=False)
    tick_signs = compute_tick_signs(prices)
    alpha = 2.0 / (max(1, IMBALANCE_EMA_SPAN) + 1.0)
    base_threshold = resolve_imbalance_base_threshold(
        IMBALANCE_MIN_TICKS,
        use_imbalance_ema_threshold=USE_IMBALANCE_EMA_THRESHOLD,
        use_imbalance_min_ticks_div3_threshold=USE_IMBALANCE_MIN_TICKS_DIV3_THRESHOLD,
    )
    expected_abs_theta = base_threshold
    bar_ids = np.empty(len(prices), dtype=np.int64)
    current_bar = 0
    ticks_in_bar = 0
    theta = 0.0

    for i, sign in enumerate(tick_signs):
        bar_ids[i] = current_bar
        ticks_in_bar += 1
        theta += float(sign)
        threshold = expected_abs_theta if USE_IMBALANCE_EMA_THRESHOLD else base_threshold
        if ticks_in_bar >= IMBALANCE_MIN_TICKS and abs(theta) >= threshold:
            if USE_IMBALANCE_EMA_THRESHOLD:
                observed = max(2.0, abs(theta))
                expected_abs_theta = (1.0 - alpha) * expected_abs_theta + alpha * observed
            current_bar += 1
            ticks_in_bar = 0
            theta = 0.0

    return bar_ids
