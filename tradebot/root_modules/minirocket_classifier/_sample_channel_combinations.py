from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _sample_channel_combinations(
    num_channels: int,
    num_combinations: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    max_num_channels = min(num_channels, 9)
    max_exponent = np.log2(max_num_channels + 1)
    num_channels_per_combination = (2 ** rng.uniform(0.0, max_exponent, num_combinations)).astype(
        np.int32
    )
    num_channels_per_combination = np.clip(num_channels_per_combination, 1, max_num_channels)

    channel_indices = np.zeros(int(num_channels_per_combination.sum()), dtype=np.int32)
    offset = 0
    for combination_index in range(num_combinations):
        count = int(num_channels_per_combination[combination_index])
        next_offset = offset + count
        channel_indices[offset:next_offset] = rng.choice(num_channels, count, replace=False)
        offset = next_offset

    return num_channels_per_combination, channel_indices
