from __future__ import annotations

from .shared import *  # noqa: F401,F403

@dataclass
class BacktestResult:
    day: str
    status: str
    from_date: str
    to_date: str
    initial_deposit: float
    final_balance: float
    profit: float
    currency: str
    leverage: str
    ticks: int
    bars: int
    duration: str
    predictions: int
    hold_skips: int
    confidence_skips: int
    position_skips: int
    stops_too_close: int
    open_failures: int
    trades_opened: int
    trades_closed: int
    wins: int
    losses: int
    realized_pnl: float
    risk_mode: str
    fixed_move: float
    stop_out: int
    tester_finished: int
    error: str
