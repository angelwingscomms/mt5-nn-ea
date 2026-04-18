from __future__ import annotations

from .shared import *  # noqa: F401,F403

class CastorTemporalBlock(nn.Module):
    def __init__(
        self,
        d_model: int,
        expand: int = 2,
        kernel_size: int = 5,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.norm = RMSNorm(d_model)
        self.d_inner = d_model * expand
        self.in_proj = nn.Linear(d_model, self.d_inner * 2)
        self.conv = CausalDepthwiseConv1d(self.d_inner, kernel_size=kernel_size)
        self.out_proj = nn.Linear(self.d_inner, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x_branch, gate_branch = self.in_proj(self.norm(x)).chunk(2, dim=-1)
        x_branch = F.gelu(self.conv(x_branch))
        x_branch = x_branch * torch.sigmoid(gate_branch)
        return residual + self.dropout(self.out_proj(x_branch))
