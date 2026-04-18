from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _compute_same_padded_response(
    sample: np.ndarray,
    channel_subset: np.ndarray,
    kernel_index: int,
    dilation: int,
) -> np.ndarray:
    selected = sample[channel_subset]
    if selected.ndim == 1:
        selected = selected[None, :]
    selected = selected.astype(np.float32, copy=False)

    kernel = BASE_KERNELS[kernel_index]
    input_length = selected.shape[1]
    padding = ((9 - 1) * dilation) // 2
    padded = np.pad(selected, ((0, 0), (padding, padding)), mode="constant")
    response = np.zeros(input_length, dtype=np.float32)

    for tap_index, weight in enumerate(kernel):
        start = tap_index * dilation
        end = start + input_length
        response += weight * padded[:, start:end].sum(axis=0)

    return response
