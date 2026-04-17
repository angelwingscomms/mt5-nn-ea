from __future__ import annotations

from .shared import *  # noqa: F401,F403

class MiniRocketClassifier(nn.Module):
    def __init__(
        self,
        parameters: MiniRocketTransformParameters,
        feature_mean: np.ndarray | None = None,
        feature_std: np.ndarray | None = None,
        n_classes: int = 3,
        token_mean: np.ndarray | None = None,
        token_std: np.ndarray | None = None,
        head_type: str = "multiattention",
        attention_dim: int = 128,
        attention_heads: int = 4,
        attention_layers: int = 2,
        attention_dropout: float = 0.1,
    ):
        super().__init__()
        self.head_type = str(head_type)
        self.backend_name = (
            "minirocket-multivariate-attention"
            if self.head_type == "multiattention"
            else "minirocket-multivariate"
        )
        self.extractor = MiniRocketFeatureExtractor(
            parameters=parameters,
            feature_mean=feature_mean,
            feature_std=feature_std,
            token_mean=token_mean,
            token_std=token_std,
        )
        if self.head_type == "linear":
            self.head = nn.Linear(self.extractor.num_features, n_classes)
        elif self.head_type == "multiattention":
            self.head = MiniRocketMultiAttentionHead(
                num_tokens=self.extractor.num_tokens,
                token_dim=self.extractor.token_feature_dim,
                n_classes=n_classes,
                model_dim=attention_dim,
                num_heads=attention_heads,
                num_layers=attention_layers,
                dropout=attention_dropout,
            )
        else:
            raise ValueError(f"Unsupported MiniRocket head_type: {self.head_type}")

    def encode_features(self, x: torch.Tensor) -> torch.Tensor:
        return self.extractor(x)

    def encode_tokens(self, x: torch.Tensor) -> torch.Tensor:
        return self.extractor.encode_tokens(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.head_type == "linear":
            return self.head(self.encode_features(x))
        return self.head(self.encode_tokens(x))
