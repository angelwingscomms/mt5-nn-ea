from __future__ import annotations

from .shared import *  # noqa: F401,F403

def rolling_population_std(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=window).std(ddof=0)
