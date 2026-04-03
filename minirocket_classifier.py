from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn


KERNEL_INDICES = np.asarray(list(combinations(range(9), 3)), dtype=np.int64)
BASE_KERNELS = np.full((len(KERNEL_INDICES), 9), -1.0, dtype=np.float32)
for kernel_index, combo in enumerate(KERNEL_INDICES):
    BASE_KERNELS[kernel_index, combo] = 2.0


@dataclass
class MiniRocketTransformParameters:
    num_channels_per_combination: np.ndarray
    channel_indices: np.ndarray
    dilations: np.ndarray
    num_features_per_dilation: np.ndarray
    biases: np.ndarray
    num_channels: int
    input_length: int

    @property
    def num_features(self) -> int:
        return int(len(self.biases))


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


def _quantiles(count: int) -> np.ndarray:
    phi = (np.sqrt(5.0) + 1.0) / 2.0
    return np.asarray([(i * phi) % 1.0 for i in range(1, count + 1)], dtype=np.float32)


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


class MiniRocketFeatureExtractor(nn.Module):
    def __init__(
        self,
        parameters: MiniRocketTransformParameters,
        feature_mean: np.ndarray | None = None,
        feature_std: np.ndarray | None = None,
    ):
        super().__init__()
        self.num_channels = int(parameters.num_channels)
        self.input_length = int(parameters.input_length)
        self.num_features = int(parameters.num_features)
        self.dilations = [int(v) for v in parameters.dilations.tolist()]
        self.num_features_per_dilation = [int(v) for v in parameters.num_features_per_dilation.tolist()]
        self.backend_name = "minirocket-multivariate"

        depthwise_weight = (
            torch.from_numpy(BASE_KERNELS).unsqueeze(1).repeat(self.num_channels, 1, 1).contiguous()
        )
        self.register_buffer("depthwise_weight", depthwise_weight)

        channel_offset = 0
        feature_offset = 0
        combination_index = 0
        for dilation_index, features_this_dilation in enumerate(self.num_features_per_dilation):
            channel_mask = np.zeros((len(KERNEL_INDICES), self.num_channels, 1), dtype=np.float32)
            bias_matrix = np.zeros((len(KERNEL_INDICES), features_this_dilation), dtype=np.float32)
            for kernel_index in range(len(KERNEL_INDICES)):
                count = int(parameters.num_channels_per_combination[combination_index])
                next_channel_offset = channel_offset + count
                channels = parameters.channel_indices[channel_offset:next_channel_offset]
                channel_mask[kernel_index, channels, 0] = 1.0

                next_feature_offset = feature_offset + features_this_dilation
                bias_matrix[kernel_index] = parameters.biases[feature_offset:next_feature_offset]

                channel_offset = next_channel_offset
                feature_offset = next_feature_offset
                combination_index += 1

            self.register_buffer(
                f"channel_mask_{dilation_index}",
                torch.from_numpy(channel_mask),
            )
            self.register_buffer(
                f"bias_matrix_{dilation_index}",
                torch.from_numpy(bias_matrix),
            )

        if feature_mean is None:
            feature_mean = np.zeros(self.num_features, dtype=np.float32)
        if feature_std is None:
            feature_std = np.ones(self.num_features, dtype=np.float32)
        feature_std = np.where(np.asarray(feature_std, dtype=np.float32) < 1e-6, 1.0, feature_std)
        self.register_buffer("feature_mean", torch.from_numpy(np.asarray(feature_mean, dtype=np.float32)))
        self.register_buffer("feature_std", torch.from_numpy(np.asarray(feature_std, dtype=np.float32)))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError("MiniRocketFeatureExtractor expects [batch, seq_len, features] input.")

        x_channels_first = x.transpose(1, 2).contiguous()
        batch_size = x_channels_first.shape[0]
        features: list[torch.Tensor] = []

        for dilation_index, dilation in enumerate(self.dilations):
            padding = ((9 - 1) * dilation) // 2
            conv = F.conv1d(
                x_channels_first,
                self.depthwise_weight,
                padding=padding,
                dilation=dilation,
                groups=self.num_channels,
            )
            conv = conv.view(batch_size, self.num_channels, len(KERNEL_INDICES), -1).permute(0, 2, 1, 3)
            response = (conv * getattr(self, f"channel_mask_{dilation_index}").unsqueeze(0)).sum(dim=2)
            bias_matrix = getattr(self, f"bias_matrix_{dilation_index}")
            should_trim = padding > 0 and (self.input_length - (2 * padding)) > 0

            for kernel_index in range(len(KERNEL_INDICES)):
                kernel_response = response[:, kernel_index, :]
                if (dilation_index + kernel_index) % 2 == 1 and should_trim:
                    kernel_response = kernel_response[:, padding:-padding]
                kernel_biases = bias_matrix[kernel_index].view(1, -1, 1)
                kernel_features = (kernel_response.unsqueeze(1) > kernel_biases).to(x.dtype).mean(dim=-1)
                features.append(kernel_features)

        output = torch.cat(features, dim=1)
        return (output - self.feature_mean) / self.feature_std


class MiniRocketClassifier(nn.Module):
    def __init__(
        self,
        parameters: MiniRocketTransformParameters,
        feature_mean: np.ndarray,
        feature_std: np.ndarray,
        n_classes: int = 3,
    ):
        super().__init__()
        self.backend_name = "minirocket-multivariate"
        self.extractor = MiniRocketFeatureExtractor(
            parameters=parameters,
            feature_mean=feature_mean,
            feature_std=feature_std,
        )
        self.head = nn.Linear(self.extractor.num_features, n_classes)

    def encode_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.extractor(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.encode_features(x))


@torch.no_grad()
def transform_sequences(
    parameters: MiniRocketTransformParameters,
    sequences: np.ndarray,
    batch_size: int = 512,
    device: str | torch.device = "cpu",
) -> np.ndarray:
    extractor = MiniRocketFeatureExtractor(parameters=parameters).to(device)
    extractor.eval()
    features: list[np.ndarray] = []
    for start in range(0, len(sequences), batch_size):
        batch = torch.from_numpy(sequences[start : start + batch_size]).to(device)
        features.append(extractor(batch).cpu().numpy())
    if not features:
        return np.empty((0, extractor.num_features), dtype=np.float32)
    return np.concatenate(features, axis=0).astype(np.float32, copy=False)


__all__ = [
    "MiniRocketClassifier",
    "MiniRocketFeatureExtractor",
    "MiniRocketTransformParameters",
    "fit_minirocket",
    "transform_sequences",
]
