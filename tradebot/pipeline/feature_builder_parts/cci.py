from __future__ import annotations

from .shared import *  # noqa: F401,F403

def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    typical = (high + low + close) / 3.0
    mean = typical.rolling(period, min_periods=period).mean()
    mean_deviation = (typical - mean).abs().rolling(period, min_periods=period).mean()
    return (typical - mean) / (0.015 * (mean_deviation + EPS))
