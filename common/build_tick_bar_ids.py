"""Fixed-tick bar id generation."""

from __future__ import annotations

import numpy as np


def build_tick_bar_ids(tick_count: int, tick_density: int) -> np.ndarray:
    return np.arange(tick_count, dtype=np.int64) // int(tick_density)
