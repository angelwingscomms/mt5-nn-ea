from __future__ import annotations

from .shared import *  # noqa: F401,F403

def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    mean = series.rolling(window, min_periods=window).mean()
    std = rolling_population_std(series, window)
    return (series - mean) / (std + EPS)
