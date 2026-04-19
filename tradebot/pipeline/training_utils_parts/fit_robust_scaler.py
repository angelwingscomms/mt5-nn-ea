from __future__ import annotations

from .shared import *  # noqa: F401,F403


def fit_robust_scaler(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fit the median/IQR scaler on one already-separated training slice."""

    if len(x) == 0:
        raise ValueError("Cannot fit scaler on an empty training slice.")

    median = np.nanmedian(x, axis=0)
    median = np.nan_to_num(median, nan=0.0)
    iqr = np.nanpercentile(x, 75, axis=0) - np.nanpercentile(x, 25, axis=0)
    iqr = np.nan_to_num(iqr, nan=1.0)
    iqr = np.where(iqr < 1e-6, 1.0, iqr)
    return median, iqr
