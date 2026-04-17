from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _quantiles(count: int) -> np.ndarray:
    phi = (np.sqrt(5.0) + 1.0) / 2.0
    return np.asarray([(i * phi) % 1.0 for i in range(1, count + 1)], dtype=np.float32)
