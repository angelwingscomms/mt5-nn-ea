from __future__ import annotations

from .shared import *  # noqa: F401,F403

def willr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    rolling_high = high.rolling(period, min_periods=period).max()
    rolling_low = low.rolling(period, min_periods=period).min()
    return -100.0 * (rolling_high - close) / (rolling_high - rolling_low + EPS)
