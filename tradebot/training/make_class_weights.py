from __future__ import annotations

from .shared import *  # noqa: F401,F403

def make_class_weights(labels: np.ndarray) -> torch.Tensor:
    counts = np.bincount(labels, minlength=3).astype(np.float32)
    weights = np.ones(3, dtype=np.float32)
    total = counts.sum()
    for cls in range(3):
        if counts[cls] > 0:
            weights[cls] = total / (3.0 * counts[cls])
    return torch.tensor(weights, dtype=torch.float32)
