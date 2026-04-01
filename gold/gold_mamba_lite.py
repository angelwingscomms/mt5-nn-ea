from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn

try:
    from mamba_ssm.modules.mamba_simple import Mamba as UpstreamMamba
except Exception as exc:  # pragma: no cover - dependency is optional in this workspace
    UpstreamMamba = None
    _UPSTREAM_IMPORT_ERROR = exc
else:
    _UPSTREAM_IMPORT_ERROR = None


class SequenceInstanceNorm(nn.Module):
    def __init__(self, n_features: int, eps: float = 1e-5, affine: bool = True):
        super().__init__()
        self.eps = eps
        self.affine = affine
        if affine:
            self.weight = nn.Parameter(torch.ones(n_features))
            self.bias = nn.Parameter(torch.zeros(n_features))
        else:
            self.register_parameter("weight", None)
            self.register_parameter("bias", None)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        mean = x.mean(dim=1, keepdim=True)
        var = x.var(dim=1, keepdim=True, unbiased=False)
        x = (x - mean) / torch.sqrt(var + self.eps)
        if self.affine:
            x = x * self.weight.view(1, 1, -1) + self.bias.view(1, 1, -1)
        return x


class RMSNorm(nn.Module):
    def __init__(self, d_model: int, eps: float = 1e-5):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(d_model))
        self.eps = eps

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        norm = torch.rsqrt(x.to(torch.float32).pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return x * norm.to(x.dtype) * self.weight


class CausalDepthwiseConv1d(nn.Module):
    def __init__(self, channels: int, kernel_size: int):
        super().__init__()
        self.left_padding = kernel_size - 1
        self.conv = nn.Conv1d(
            in_channels=channels,
            out_channels=channels,
            kernel_size=kernel_size,
            groups=channels,
            bias=True,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = F.pad(x, (self.left_padding, 0))
        x = self.conv(x)
        return x.transpose(1, 2)


class PortableMambaMixer(nn.Module):
    def __init__(
        self,
        d_model: int,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        dt_rank: int | str = "auto",
    ):
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_inner = d_model * expand
        self.dt_rank = max(1, (d_model + 15) // 16) if dt_rank == "auto" else int(dt_rank)

        self.in_proj = nn.Linear(d_model, self.d_inner * 2, bias=False)
        self.conv = CausalDepthwiseConv1d(self.d_inner, d_conv)
        self.x_proj = nn.Linear(self.d_inner, self.dt_rank + d_state * 2, bias=False)
        self.dt_proj = nn.Linear(self.dt_rank, self.d_inner, bias=True)

        dt = torch.exp(
            torch.rand(self.d_inner) * (math.log(0.1) - math.log(0.001)) + math.log(0.001)
        ).clamp(min=1e-4)
        inv_dt = dt + torch.log(-torch.expm1(-dt))
        with torch.no_grad():
            self.dt_proj.bias.copy_(inv_dt)

        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

        a = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        a = a + torch.rand_like(a) * 0.1
        self.A_log = nn.Parameter(torch.log(a))
        self.D = nn.Parameter(torch.ones(self.d_inner))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_branch, z_branch = self.in_proj(x).chunk(2, dim=-1)
        x_branch = F.silu(self.conv(x_branch))
        params = self.x_proj(x_branch)
        delta, b_term, c_term = torch.split(
            params, [self.dt_rank, self.d_state, self.d_state], dim=-1
        )
        delta = F.softplus(self.dt_proj(delta))
        y = self._selective_scan(x_branch, delta, b_term, c_term)
        y = y * F.silu(z_branch)
        return self.out_proj(y)

    def _selective_scan(
        self,
        u: torch.Tensor,
        delta: torch.Tensor,
        b_term: torch.Tensor,
        c_term: torch.Tensor,
    ) -> torch.Tensor:
        batch_size, seq_len, _ = u.shape
        a = -torch.exp(self.A_log).to(dtype=u.dtype, device=u.device)
        d = self.D.to(dtype=u.dtype, device=u.device)
        state = torch.zeros(
            (batch_size, self.d_inner, self.d_state),
            device=u.device,
            dtype=torch.float32,
        )
        outputs = []

        delta_a = torch.exp(delta.unsqueeze(-1) * a.unsqueeze(0).unsqueeze(0)).to(torch.float32)
        delta_b_u = (delta * u).unsqueeze(-1) * b_term.unsqueeze(2)
        delta_b_u = delta_b_u.to(torch.float32)
        c_term = c_term.to(torch.float32)
        u_f32 = u.to(torch.float32)
        d_f32 = d.to(torch.float32)

        for t in range(seq_len):
            state = delta_a[:, t] * state + delta_b_u[:, t]
            y_t = (state * c_term[:, t].unsqueeze(1)).sum(dim=-1) + d_f32 * u_f32[:, t]
            outputs.append(y_t)

        return torch.stack(outputs, dim=1).to(u.dtype)


class MambaLiteResidualBlock(nn.Module):
    def __init__(
        self,
        d_model: int,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
        dt_rank: int | str = "auto",
        dropout: float = 0.1,
        prefer_upstream: bool = True,
    ):
        super().__init__()
        self.norm = RMSNorm(d_model)
        if prefer_upstream and UpstreamMamba is not None:
            self.mixer = UpstreamMamba(d_model=d_model, d_state=d_state, d_conv=d_conv, expand=expand)
            self.backend_name = "MambaLite-Micro/mamba_simple"
        else:
            self.mixer = PortableMambaMixer(
                d_model=d_model,
                d_state=d_state,
                d_conv=d_conv,
                expand=expand,
                dt_rank=dt_rank,
            )
            reason = ""
            if prefer_upstream and _UPSTREAM_IMPORT_ERROR is not None:
                reason = f" (fallback: {_UPSTREAM_IMPORT_ERROR.__class__.__name__})"
            self.backend_name = f"portable-mamba-lite{reason}"
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.dropout(self.mixer(self.norm(x)))


class GoldMambaLiteClassifier(nn.Module):
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
        prefer_upstream: bool = True,
    ):
        super().__init__()
        self.d_model = d_model
        self.sequence_norm = SequenceInstanceNorm(n_features) if use_sequence_norm else nn.Identity()
        self.embedding = nn.Linear(n_features, d_model) if d_model != n_features else nn.Identity()
        self.layers = nn.ModuleList(
            [
                MambaLiteResidualBlock(
                    d_model=d_model,
                    d_state=d_state,
                    d_conv=d_conv,
                    expand=expand,
                    dt_rank=dt_rank,
                    dropout=dropout,
                    prefer_upstream=prefer_upstream,
                )
                for _ in range(n_layers)
            ]
        )
        self.backend_name = self.layers[0].backend_name if self.layers else "no-layers"
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
        return self.head(self.encode_last(x))


__all__ = ["GoldMambaLiteClassifier"]
