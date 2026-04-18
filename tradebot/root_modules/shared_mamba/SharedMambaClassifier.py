from __future__ import annotations

from .shared import *  # noqa: F401,F403

class SharedMambaClassifier(nn.Module):
    def __init__(
        self,
        n_features: int,
        d_model: int = 128,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        hidden: int = 256,
        n_classes: int = 3,
        dropout: float = 0.4,
        n_layers: int = 2,
        dt_rank: int | str = "auto",
        use_sequence_norm: bool = False,
    ):
        super().__init__()
        self.d_model = d_model
        self.sequence_norm = SequenceInstanceNorm(n_features) if use_sequence_norm else nn.Identity()
        self.embedding = nn.Linear(n_features, d_model) if d_model != n_features else nn.Identity()
        self.layers = nn.ModuleList(
            [
                ResidualMambaBlock(
                    d_model=d_model,
                    d_state=d_state,
                    d_conv=d_conv,
                    expand=expand,
                    dt_rank=dt_rank,
                    dropout=dropout,
                )
                for _ in range(n_layers)
            ]
        )
        self.norm = RMSNorm(d_model)
        self.head = nn.Sequential(
            nn.Linear(d_model, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, n_classes),
        )

    def encode_sequence(self, x: torch.Tensor) -> torch.Tensor:
        x = self.sequence_norm(x)
        x = self.embedding(x)
        for layer in self.layers:
            x = layer(x)
        return self.norm(x)

    def encode_last(self, x: torch.Tensor) -> torch.Tensor:
        x = self.encode_sequence(x)
        return x[:, -1, :]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.encode_last(x)
        return self.head(x)
