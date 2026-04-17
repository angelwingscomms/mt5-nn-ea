from __future__ import annotations

from .shared import *  # noqa: F401,F403
from tradebot.pipeline.windowing import choose_evenly_spaced

def maybe_cap_windows(indices: np.ndarray, max_count: int, use_all_windows: bool) -> np.ndarray:
    if use_all_windows:
        return indices.astype(np.int64, copy=False)
    return choose_evenly_spaced(indices, max_count)
