"""Fixed-time bar id generation."""

from __future__ import annotations

import numpy as np


def build_time_bar_ids(time_msc: np.ndarray, bar_duration_ms: int) -> np.ndarray:
    return time_msc // bar_duration_ms
