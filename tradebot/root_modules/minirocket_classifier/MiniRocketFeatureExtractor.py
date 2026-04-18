from __future__ import annotations

from .shared import *  # noqa: F401,F403

class MiniRocketFeatureExtractor(nn.Module):
    def __init__(
        self,
        parameters: MiniRocketTransformParameters,
        feature_mean: np.ndarray | None = None,
        feature_std: np.ndarray | None = None,
        token_mean: np.ndarray | None = None,
        token_std: np.ndarray | None = None,
    ):
        super().__init__()
        self.num_channels = int(parameters.num_channels)
        self.input_length = int(parameters.input_length)
        self.num_features = int(parameters.num_features)
        self.num_kernels = len(KERNEL_INDICES)
        self.dilations = [int(v) for v in parameters.dilations.tolist()]
        self.num_features_per_dilation = [int(v) for v in parameters.num_features_per_dilation.tolist()]
        self.num_tokens = int(parameters.num_tokens)
        self.max_features_per_dilation = int(parameters.max_features_per_dilation)
        self.token_feature_dim = int(parameters.token_feature_dim)
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

        if token_mean is None:
            token_mean = np.zeros((self.num_tokens, self.token_feature_dim), dtype=np.float32)
        if token_std is None:
            token_std = np.ones((self.num_tokens, self.token_feature_dim), dtype=np.float32)
        token_std = np.where(np.asarray(token_std, dtype=np.float32) < 1e-6, 1.0, token_std)
        self.register_buffer("token_mean", torch.from_numpy(np.asarray(token_mean, dtype=np.float32)))
        self.register_buffer("token_std", torch.from_numpy(np.asarray(token_std, dtype=np.float32)))

    def _extract_raw_features(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if x.ndim != 3:
            raise ValueError("MiniRocketFeatureExtractor expects [batch, seq_len, features] input.")

        x_channels_first = x.transpose(1, 2).contiguous()
        batch_size = x_channels_first.shape[0]
        flat_features: list[torch.Tensor] = []
        token_features: list[torch.Tensor] = []

        for dilation_index, dilation in enumerate(self.dilations):
            padding = ((9 - 1) * dilation) // 2
            conv = F.conv1d(
                x_channels_first,
                self.depthwise_weight,
                padding=padding,
                dilation=dilation,
                groups=self.num_channels,
            )
            conv = conv.view(batch_size, self.num_channels, self.num_kernels, -1).permute(0, 2, 1, 3)
            response = (conv * getattr(self, f"channel_mask_{dilation_index}").unsqueeze(0)).sum(dim=2)
            bias_matrix = getattr(self, f"bias_matrix_{dilation_index}")
            should_trim = padding > 0 and (self.input_length - (2 * padding)) > 0
            token_block = x.new_zeros((batch_size, self.num_kernels, self.max_features_per_dilation))

            for kernel_index in range(self.num_kernels):
                kernel_response = response[:, kernel_index, :]
                if (dilation_index + kernel_index) % 2 == 1 and should_trim:
                    kernel_response = kernel_response[:, padding:-padding]
                kernel_biases = bias_matrix[kernel_index].view(1, -1, 1)
                kernel_features = (kernel_response.unsqueeze(1) > kernel_biases).to(x.dtype).mean(dim=-1)
                flat_features.append(kernel_features)
                token_block[:, kernel_index, : kernel_features.shape[1]] = kernel_features

            token_features.append(token_block.reshape(batch_size, -1))

        flat_output = torch.cat(flat_features, dim=1)
        token_output = torch.stack(token_features, dim=1)
        return flat_output, token_output

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _token_output = self._extract_raw_features(x)
        return (output - self.feature_mean) / self.feature_std

    def encode_tokens(self, x: torch.Tensor) -> torch.Tensor:
        _flat_output, token_output = self._extract_raw_features(x)
        return (token_output - self.token_mean) / self.token_std
