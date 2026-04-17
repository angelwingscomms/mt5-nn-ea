from __future__ import annotations

from .shared import *  # noqa: F401,F403

class MambaLiteResidualBlock(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1):
        super().__init__()
        self.norm = RMSNorm(d_model)
        self.mixer = PortableMambaMixer(d_model=d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.dropout(self.mixer(self.norm(x)))
