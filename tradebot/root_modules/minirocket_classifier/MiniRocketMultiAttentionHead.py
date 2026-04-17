from __future__ import annotations

from .shared import *  # noqa: F401,F403

class MiniRocketMultiAttentionHead(nn.Module):
    def __init__(
        self,
        num_tokens: int,
        token_dim: int,
        n_classes: int = 3,
        model_dim: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        dropout: float = 0.1,
    ):
        super().__init__()
        if num_tokens <= 0:
            raise ValueError("MiniRocketMultiAttentionHead requires at least one token.")
        if token_dim <= 0:
            raise ValueError("MiniRocketMultiAttentionHead requires token_dim > 0.")
        if num_heads <= 0:
            raise ValueError("MiniRocketMultiAttentionHead requires num_heads > 0.")
        if num_layers <= 0:
            raise ValueError("MiniRocketMultiAttentionHead requires num_layers > 0.")

        self.num_tokens = int(num_tokens)
        self.token_dim = int(token_dim)
        self.num_heads = int(num_heads)
        self.model_dim = max(self.num_heads, int(model_dim))
        if self.model_dim % self.num_heads != 0:
            self.model_dim += self.num_heads - (self.model_dim % self.num_heads)

        self.token_projection = nn.Linear(self.token_dim, self.model_dim)
        self.position_embedding = nn.Parameter(torch.zeros(1, self.num_tokens, self.model_dim))
        self.input_dropout = nn.Dropout(dropout)
        self.layers = nn.ModuleList(
            MiniRocketAttentionBlock(
                model_dim=self.model_dim,
                num_heads=self.num_heads,
                dropout=dropout,
            )
            for _ in range(int(num_layers))
        )
        self.pool_projection = nn.Linear(self.model_dim, 1)
        self.classifier = nn.Sequential(
            nn.LayerNorm(self.model_dim * 2),
            nn.Linear(self.model_dim * 2, self.model_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(self.model_dim, n_classes),
        )

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        if tokens.ndim != 3:
            raise ValueError("MiniRocketMultiAttentionHead expects [batch, tokens, token_dim] input.")

        x = self.input_dropout(self.token_projection(tokens) + self.position_embedding[:, : tokens.shape[1]])
        for layer in self.layers:
            x = layer(x)
        pool_weights = torch.softmax(self.pool_projection(x).squeeze(-1), dim=-1)
        pooled = torch.sum(x * pool_weights.unsqueeze(-1), dim=1)
        summary = x.mean(dim=1)
        return self.classifier(torch.cat([pooled, summary], dim=1))
