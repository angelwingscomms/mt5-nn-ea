from __future__ import annotations

from .shared import *  # noqa: F401,F403

class RMSNorm(nn.Module):
    def __init__(self, d_model: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d_model))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Cast to float32 before squaring to prevent FP16 overflow
        norm = torch.rsqrt(x.to(torch.float32).pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * norm.to(x.dtype) * self.weight
