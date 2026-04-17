from __future__ import annotations

from .shared import *  # noqa: F401,F403

def choose_confidence_threshold(
    probs: np.ndarray,
    labels: np.ndarray,
    *,
    min_selected: int,
    threshold_min: float,
    threshold_max: float,
    threshold_steps: int,
) -> float:
    preds = probs.argmax(axis=1)
    confidences = probs.max(axis=1)
    is_binary = probs.shape[1] == 2
    candidate_mask = np.ones(len(preds), dtype=bool) if is_binary else preds > 0
    threshold_min = min(max(0.0, float(threshold_min)), 0.999999)
    threshold_max = min(max(threshold_min, float(threshold_max)), 0.999999)
    threshold_steps = max(2, int(threshold_steps))
    candidate_count = len(preds) if is_binary else int(candidate_mask.sum())
    if candidate_count == 0:
        log.warning(
            "Confidence gate selection: model produced no BUY/SELL predictions; falling back to threshold %.2f.",
            threshold_min,
        )
        return threshold_min

    min_selected = max(1, min_selected)
    best_threshold = threshold_min
    best_precision = -1.0
    best_selected = -1
    best_coverage = -1.0
    relaxed_threshold = threshold_min
    relaxed_precision = -1.0
    relaxed_selected = -1
    relaxed_coverage = -1.0
    found_candidate = False
    found_relaxed_candidate = False

    for threshold in np.linspace(threshold_min, threshold_max, threshold_steps):
        selected = candidate_mask & (confidences >= threshold)
        selected_count = int(selected.sum())
        if selected_count == 0:
            continue

        precision = float((preds[selected] == labels[selected]).mean())
        coverage = float(selected.mean())
        found_relaxed_candidate = True
        if precision > relaxed_precision + 1e-12 or (
            abs(precision - relaxed_precision) <= 1e-12
            and (selected_count > relaxed_selected or (selected_count == relaxed_selected and coverage > relaxed_coverage))
        ):
            relaxed_threshold = float(threshold)
            relaxed_precision = precision
            relaxed_selected = selected_count
            relaxed_coverage = coverage

        if selected_count < min_selected:
            continue
        found_candidate = True
        if precision > best_precision + 1e-12 or (
            abs(precision - best_precision) <= 1e-12
            and (selected_count > best_selected or (selected_count == best_selected and coverage > best_coverage))
        ):
            best_threshold = float(threshold)
            best_precision = precision
            best_selected = selected_count
            best_coverage = coverage

    if found_candidate:
        print("Chosen confidence threshold: %.2f with precision %.4f and coverage %.4f" % (best_threshold, best_precision, best_coverage))
        return best_threshold
    if found_relaxed_candidate:
        log.warning(
            "Confidence gate selection: no threshold produced at least %d BUY/SELL trades; "
            "falling back to threshold %.2f with %d trades and precision %.4f.",
            min_selected,
            relaxed_threshold,
            relaxed_selected,
            relaxed_precision,
        )
        print(
            "Chosen confidence threshold: %.2f with precision %.4f and coverage %.4f"
            % (relaxed_threshold, relaxed_precision, relaxed_coverage)
        )
        return relaxed_threshold

    log.warning(
        "Confidence gate selection: no threshold selected any BUY/SELL trades; falling back to threshold %.2f.",
        threshold_min,
    )
    return threshold_min
