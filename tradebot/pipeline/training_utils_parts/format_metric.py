from __future__ import annotations

from .shared import *  # noqa: F401,F403

def format_metric(value: float) -> str:
    return f"{value:.4f}" if np.isfinite(value) else "n/a"
