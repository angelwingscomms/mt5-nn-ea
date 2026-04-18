from __future__ import annotations

from .shared import *  # noqa: F401,F403

def fit_minirocket(
    x_train_channels_first: np.ndarray,
    num_features: int = 10_080,
    max_dilations_per_kernel: int = 32,
    seed: int = 42,
) -> MiniRocketTransformParameters:
    x_train = np.asarray(x_train_channels_first, dtype=np.float32)
    if x_train.ndim != 3:
        raise ValueError("MiniRocket expects training input in [examples, channels, length] format.")

    num_examples, num_channels, input_length = x_train.shape
    if num_examples == 0:
        raise ValueError("MiniRocket fitting requires at least one training example.")
    if input_length < 9:
        raise ValueError("MiniRocket requires sequence length >= 9.")

    num_kernels = len(KERNEL_INDICES)
    rounded_features = max(num_kernels, num_kernels * ((num_features + num_kernels - 1) // num_kernels))
    dilations, num_features_per_dilation = _fit_dilations(
        input_length=input_length,
        num_features=rounded_features,
        max_dilations_per_kernel=max_dilations_per_kernel,
    )
    num_features_per_kernel = int(np.sum(num_features_per_dilation))
    quantiles = _quantiles(num_kernels * num_features_per_kernel)
    num_combinations = num_kernels * len(dilations)
    rng = np.random.default_rng(seed)
    num_channels_per_combination, channel_indices = _sample_channel_combinations(
        num_channels=num_channels,
        num_combinations=num_combinations,
        rng=rng,
    )

    biases = np.zeros(num_kernels * num_features_per_kernel, dtype=np.float32)
    feature_offset = 0
    channel_offset = 0
    combination_index = 0
    for dilation_index, dilation in enumerate(dilations):
        features_this_dilation = int(num_features_per_dilation[dilation_index])
        for kernel_index in range(num_kernels):
            feature_end = feature_offset + features_this_dilation
            channel_count = int(num_channels_per_combination[combination_index])
            channel_end = channel_offset + channel_count
            channel_subset = channel_indices[channel_offset:channel_end]
            sample = x_train[int(rng.integers(num_examples))]
            response = _compute_same_padded_response(
                sample=sample,
                channel_subset=channel_subset,
                kernel_index=kernel_index,
                dilation=int(dilation),
            )
            biases[feature_offset:feature_end] = np.quantile(
                response,
                quantiles[feature_offset:feature_end],
            ).astype(np.float32)

            feature_offset = feature_end
            channel_offset = channel_end
            combination_index += 1

    return MiniRocketTransformParameters(
        num_channels_per_combination=num_channels_per_combination,
        channel_indices=channel_indices,
        dilations=dilations,
        num_features_per_dilation=num_features_per_dilation,
        biases=biases,
        num_channels=num_channels,
        input_length=input_length,
    )
