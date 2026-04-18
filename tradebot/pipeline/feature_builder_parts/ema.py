from __future__ import annotations

from .shared import *  # noqa: F401,F403

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()
