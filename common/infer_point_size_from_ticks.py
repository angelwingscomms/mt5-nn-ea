"""Infer point size from raw bid/ask ticks."""

from __future__ import annotations

import numpy as np


def infer_point_size_from_ticks(df_ticks, max_samples: int = 200_000) -> float:
    prices = np.concatenate([
        df_ticks["bid"].to_numpy(dtype=np.float64, copy=False),
        df_ticks["ask"].to_numpy(dtype=np.float64, copy=False),
    ])
    prices = prices[np.isfinite(prices)]
    if len(prices) == 0:
        return 1.0

    sample = np.round(prices[:max_samples], 8)
    unique_prices = np.unique(sample)
    if len(unique_prices) < 2:
        return 1.0

    scaled = np.rint(unique_prices * 1e8).astype(np.int64)
    diffs = np.diff(scaled)
    diffs = diffs[diffs > 0]
    if len(diffs) == 0:
        return 1.0

    gcd_points = int(np.gcd.reduce(diffs[:min(len(diffs), 50_000)]))
    point_size = gcd_points / 1e8 if gcd_points > 0 else 1.0
    return float(point_size if point_size > 0.0 else 1.0)
