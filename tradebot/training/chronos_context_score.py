from __future__ import annotations

from .shared import *  # noqa: F401,F403

def chronos_context_score(metrics: dict[str, float | int], min_selected: int) -> tuple[float, float, int, float]:
    selected_trades = int(metrics["selected_trades"])
    precision = float(metrics["precision"])
    precision_score = precision if np.isfinite(precision) else -1.0
    return (
        float(selected_trades >= min_selected),
        precision_score,
        selected_trades,
        float(metrics["trade_coverage"]),
    )
