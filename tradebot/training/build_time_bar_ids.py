from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_time_bar_ids(time_msc: np.ndarray) -> np.ndarray:
    if PRIMARY_BAR_SECONDS <= 0:
        raise ValueError("PRIMARY_BAR_SECONDS must be positive.")
    return time_msc // BAR_DURATION_MS
