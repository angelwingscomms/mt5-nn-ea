from __future__ import annotations

from .shared import *  # noqa: F401,F403

def summarize_numeric(values: np.ndarray, label: str) -> list[str]:
    array = np.asarray(values, dtype=np.float64)
    return [
        f"{label} min={array.min():.2f}",
        f"{label} p50={np.percentile(array, 50):.2f}",
        f"{label} p90={np.percentile(array, 90):.2f}",
        f"{label} p99={np.percentile(array, 99):.2f}",
        f"{label} mean={array.mean():.2f}",
        f"{label} max={array.max():.2f}",
    ]
