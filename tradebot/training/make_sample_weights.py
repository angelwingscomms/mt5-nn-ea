from __future__ import annotations

from .shared import *  # noqa: F401,F403

def make_sample_weights(labels: np.ndarray) -> torch.Tensor:
    class_weights = make_class_weights(labels).to(torch.float64).numpy()
    sample_weights = class_weights[labels.astype(np.int64)]
    sample_weights /= max(sample_weights.mean(), 1e-12)
    return torch.tensor(sample_weights, dtype=torch.double)
