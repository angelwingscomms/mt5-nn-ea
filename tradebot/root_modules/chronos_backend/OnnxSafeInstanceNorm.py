from __future__ import annotations

from .shared import *  # noqa: F401,F403

class OnnxSafeInstanceNorm(nn.Module):
    """ONNX-safe replacement for Chronos-Bolt instance normalization on dense contexts."""

    def __init__(self, eps: float = 1e-5, use_arcsinh: bool = False) -> None:
        super().__init__()
        self.eps = float(eps)
        self.use_arcsinh = bool(use_arcsinh)

    def forward(
        self,
        x: torch.Tensor,
        loc_scale: tuple[torch.Tensor, torch.Tensor] | None = None,
    ) -> tuple[torch.Tensor, tuple[torch.Tensor, torch.Tensor]]:
        orig_dtype = x.dtype
        x = x.to(torch.float32)
        if loc_scale is None:
            # Our exported MT5 feature windows are fully observed, so plain mean/variance
            # matches Chronos-Bolt's masked normalization without relying on nanmean.
            loc = x.mean(dim=-1, keepdim=True)
            scale = (x - loc).square().mean(dim=-1, keepdim=True).sqrt()
            scale = torch.clamp_min(scale, self.eps)
        else:
            loc, scale = loc_scale

        scaled_x = (x - loc) / scale
        if self.use_arcsinh:
            scaled_x = torch.arcsinh(scaled_x)
        return scaled_x.to(orig_dtype), (loc, scale)

    def inverse(self, x: torch.Tensor, loc_scale: tuple[torch.Tensor, torch.Tensor]) -> torch.Tensor:
        orig_dtype = x.dtype
        x = x.to(torch.float32)
        loc, scale = loc_scale
        if self.use_arcsinh:
            x = torch.sinh(x)
        return (x * scale + loc).to(orig_dtype)
