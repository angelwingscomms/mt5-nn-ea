from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_tick_bar_ids(tick_count: int, tick_density: int) -> np.ndarray:
    if tick_density <= 0:
        raise ValueError("PRIMARY_TICK_DENSITY must be positive.")
    return np.arange(tick_count, dtype=np.int64) // int(tick_density)
