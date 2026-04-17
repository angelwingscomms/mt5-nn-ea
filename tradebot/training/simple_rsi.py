from __future__ import annotations

from .shared import *  # noqa: F401,F403

def simple_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    avg_gain = gains.rolling(period, min_periods=period).mean()
    avg_loss = losses.rolling(period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + EPS)
    return (100.0 - (100.0 / (1.0 + rs)) - 50.0) / 50.0
