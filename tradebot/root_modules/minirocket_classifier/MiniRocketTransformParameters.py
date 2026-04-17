from __future__ import annotations

from .shared import *  # noqa: F401,F403

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

    @property
    def num_tokens(self) -> int:
        return int(len(self.dilations))

    @property
    def max_features_per_dilation(self) -> int:
        if len(self.num_features_per_dilation) == 0:
            return 0
        return int(np.max(self.num_features_per_dilation))

    @property
    def token_feature_dim(self) -> int:
        return int(len(KERNEL_INDICES) * self.max_features_per_dilation)
