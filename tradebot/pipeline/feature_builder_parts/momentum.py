from __future__ import annotations

from .shared import *  # noqa: F401,F403

def momentum(close: pd.Series, period: int) -> pd.Series:
    return close - close.shift(period)
