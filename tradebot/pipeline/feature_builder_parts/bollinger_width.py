from __future__ import annotations

from .shared import *  # noqa: F401,F403

def bollinger_width(close: pd.Series, period: int) -> pd.Series:
    mean = close.rolling(period, min_periods=period).mean()
    std = rolling_population_std(close, period)
    upper = mean + (2.0 * std)
    lower = mean - (2.0 * std)
    return (upper - lower) / (mean + EPS)
