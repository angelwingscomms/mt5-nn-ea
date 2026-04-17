from __future__ import annotations

from .shared import *  # noqa: F401,F403

def error_result(day_value: date, error: str) -> BacktestResult:
    return BacktestResult(
        day=day_value.isoformat(),
        status="error",
        from_date=day_value.strftime("%Y.%m.%d"),
        to_date=(day_value + timedelta(days=1)).strftime("%Y.%m.%d"),
        initial_deposit=0.0,
        final_balance=0.0,
        profit=0.0,
        currency="",
        leverage="",
        ticks=0,
        bars=0,
        duration="",
        predictions=0,
        hold_skips=0,
        confidence_skips=0,
        position_skips=0,
        stops_too_close=0,
        open_failures=0,
        trades_opened=0,
        trades_closed=0,
        wins=0,
        losses=0,
        realized_pnl=0.0,
        risk_mode="",
        fixed_move=0.0,
        stop_out=0,
        tester_finished=0,
        error=error,
    )
