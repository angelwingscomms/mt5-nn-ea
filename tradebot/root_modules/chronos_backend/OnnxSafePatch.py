from __future__ import annotations

from .shared import *  # noqa: F401,F403

class OnnxSafePatch(nn.Module):
    """Patch dense sequences without `unfold`, which the legacy ONNX exporter rejects here."""

    def __init__(self, patch_size: int, patch_stride: int) -> None:
        super().__init__()
        self.patch_size = int(patch_size)
        self.patch_stride = int(patch_stride)
        if self.patch_stride != self.patch_size:
            raise ValueError(
                "OnnxSafePatch currently supports only non-overlapping Chronos-Bolt patches "
                f"(patch_size={self.patch_size}, patch_stride={self.patch_stride})."
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        length = x.shape[-1]
        remainder = length % self.patch_size
        if remainder != 0:
            padding = torch.zeros(
                (*x.shape[:-1], self.patch_size - remainder),
                dtype=x.dtype,
                device=x.device,
            )
            x = torch.cat((padding, x), dim=-1)
        patch_count = x.shape[-1] // self.patch_size
        return x.contiguous().reshape(*x.shape[:-1], patch_count, self.patch_size)
