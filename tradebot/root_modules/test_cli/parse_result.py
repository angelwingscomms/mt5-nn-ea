from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_result(day_value: date, tester_text: str, agent_text: str) -> BacktestResult:
    initial_deposit = 0.0
    final_balance = 0.0
    currency = ""
    leverage = ""
    ticks = 0
    bars = 0
    duration = ""
    from_date = day_value.strftime("%Y.%m.%d")
    to_date = (day_value + timedelta(days=1)).strftime("%Y.%m.%d")
    error = ""

    for line in agent_text.splitlines():
        initial_match = INITIAL_DEPOSIT_PATTERN.search(line)
        if initial_match:
            initial_deposit = float(initial_match.group(1))
            currency = initial_match.group(2)
            leverage = initial_match.group(3)

        final_match = FINAL_BALANCE_PATTERN.search(line)
        if final_match:
            final_balance = float(final_match.group(1))
            if not currency:
                currency = final_match.group(2)

        generated_match = GENERATED_PATTERN.search(line)
        if generated_match:
            ticks = int(generated_match.group(1))
            bars = int(generated_match.group(2))
            duration = generated_match.group(3)

        status_match = STATUS_LINE_PATTERN.search(line)
        if status_match:
            from_date = status_match.group(1)
            to_date = status_match.group(2)

    summary_values = parse_summary_text(agent_text)
    tester_finished = int("automatical testing finished" in tester_text.lower())
    stop_out = int("stop out" in agent_text.lower())

    if not agent_text.strip():
        error = "agent_log_missing"
    elif final_balance == 0.0 and initial_deposit == 0.0 and ticks == 0 and bars == 0:
        error = "summary_not_found"

    status = "ok"
    if error:
        status = "error"
    elif ticks == 0 and bars == 0:
        status = "no_data"
    elif stop_out:
        status = "stop_out"

    return BacktestResult(
        day=day_value.isoformat(),
        status=status,
        from_date=from_date,
        to_date=to_date,
        initial_deposit=initial_deposit,
        final_balance=final_balance,
        profit=final_balance - initial_deposit,
        currency=currency,
        leverage=leverage,
        ticks=ticks,
        bars=bars,
        duration=duration,
        predictions=int(summary_values.get("predictions", 0)),
        hold_skips=int(summary_values.get("hold_skips", 0)),
        confidence_skips=int(summary_values.get("confidence_skips", 0)),
        position_skips=int(summary_values.get("position_skips", 0)),
        stops_too_close=int(summary_values.get("stops_too_close", 0)),
        open_failures=int(summary_values.get("open_failures", 0)),
        trades_opened=int(summary_values.get("trades_opened", 0)),
        trades_closed=int(summary_values.get("trades_closed", 0)),
        wins=int(summary_values.get("wins", 0)),
        losses=int(summary_values.get("losses", 0)),
        realized_pnl=float(summary_values.get("realized_pnl", 0.0)),
        risk_mode=str(summary_values.get("risk_mode", "")),
        fixed_move=float(summary_values.get("fixed_move", 0.0)),
        stop_out=stop_out,
        tester_finished=tester_finished,
        error=error,
    )
