from __future__ import annotations

from .shared import *  # noqa: F401,F403

def class_count_lines(labels: np.ndarray, label_names: tuple[str, ...]) -> list[str]:
    counts = np.bincount(labels, minlength=len(label_names))
    return [f"{label_names[i]}: {int(counts[i])}" for i in range(len(label_names))]
