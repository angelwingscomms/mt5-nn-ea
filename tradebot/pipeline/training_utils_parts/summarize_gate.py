from __future__ import annotations

from .shared import *  # noqa: F401,F403

def summarize_gate(name: str, probs: np.ndarray, labels: np.ndarray, threshold: float) -> dict[str, float | int]:
    metrics = gate_metrics(labels, probs, threshold)
    if metrics["selected_trades"]:
        log.info(
            "%s: threshold=%.2f precision=%.4f coverage=%.4f trades=%d mean_selected_conf=%.4f",
            name,
            threshold,
            float(metrics["precision"]),
            float(metrics["trade_coverage"]),
            int(metrics["selected_trades"]),
            float(metrics["selected_mean_confidence"]),
        )
    else:
        log.warning("%s: threshold=%.2f produced no trades.", name, threshold)
    return metrics
