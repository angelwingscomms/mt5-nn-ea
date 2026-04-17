from __future__ import annotations

from .shared import *  # noqa: F401,F403

def macd_components(close: pd.Series, fast_period: int, slow_period: int, signal_period: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = ema(close, fast_period)
    slow = ema(close, slow_period)
    line = fast - slow
    signal = line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    hist = line - signal
    return line, signal, hist
