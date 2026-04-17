from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _fit_dilations(
    input_length: int,
    num_features: int,
    max_dilations_per_kernel: int,
) -> tuple[np.ndarray, np.ndarray]:
    num_kernels = len(KERNEL_INDICES)
    num_features_per_kernel = max(1, num_features // num_kernels)
    true_max_dilations_per_kernel = min(num_features_per_kernel, max_dilations_per_kernel)
    multiplier = num_features_per_kernel / true_max_dilations_per_kernel

    max_exponent = np.log2((input_length - 1) / (9 - 1))
    dilations, num_features_per_dilation = np.unique(
        np.logspace(0, max_exponent, true_max_dilations_per_kernel, base=2).astype(np.int32),
        return_counts=True,
    )
    num_features_per_dilation = (num_features_per_dilation * multiplier).astype(np.int32)

    remainder = num_features_per_kernel - int(np.sum(num_features_per_dilation))
    i = 0
    while remainder > 0:
        num_features_per_dilation[i] += 1
        remainder -= 1
        i = (i + 1) % len(num_features_per_dilation)

    return dilations.astype(np.int32), num_features_per_dilation.astype(np.int32)
