from __future__ import annotations

from .shared import *  # noqa: F401,F403

def write_report(path: Path, scope_label: str, rows: list[BacktestResult], daily_mode: bool) -> None:
    total_profit = sum(row.profit for row in rows)
    profitable_days = sum(1 for row in rows if row.profit > 0.0)
    losing_days = sum(1 for row in rows if row.profit < 0.0)
    no_data_days = sum(1 for row in rows if row.status == "no_data")
    stop_out_days = sum(1 for row in rows if row.stop_out)
    total_trades = sum(row.trades_opened for row in rows)
    total_closed = sum(row.trades_closed for row in rows)
    total_predictions = sum(row.predictions for row in rows)
    total_realized = sum(row.realized_pnl for row in rows)

    lines = [
        "# Daily Backtest Report",
        "",
        f"- {'day' if daily_mode else 'month'}: {scope_label}",
        f"- days_tested: {len(rows)}",
        f"- profitable_days: {profitable_days}",
        f"- losing_days: {losing_days}",
        f"- no_data_days: {no_data_days}",
        f"- stop_out_days: {stop_out_days}",
        f"- total_profit: {total_profit:.2f}",
        f"- total_realized_pnl: {total_realized:.2f}",
        f"- total_predictions: {total_predictions}",
        f"- total_trades_opened: {total_trades}",
        f"- total_trades_closed: {total_closed}",
        "",
        "| day | status | profit | final_balance | trades_opened | trades_closed | wins | losses | ticks | bars | risk_mode | error |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    for row in rows:
        lines.append(
            f"| {row.day} | {row.status} | {row.profit:.2f} | {row.final_balance:.2f} | "
            f"{row.trades_opened} | {row.trades_closed} | {row.wins} | {row.losses} | "
            f"{row.ticks} | {row.bars} | {row.risk_mode or '-'} | {row.error or '-'} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
