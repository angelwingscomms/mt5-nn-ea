from __future__ import annotations

from .shared import *  # noqa: F401,F403

def simple_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    return true_range(high, low, close).rolling(period, min_periods=period).mean()
