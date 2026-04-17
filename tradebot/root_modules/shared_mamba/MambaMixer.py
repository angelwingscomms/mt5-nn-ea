from __future__ import annotations

from .shared import *  # noqa: F401,F403

class MambaMixer(nn.Module):
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

        # Initialize dt bias so that F.softplus(dt_bias) is between exp(-4) and exp(-3)
        dt = torch.exp(
            torch.rand(self.d_inner) * (math.log(0.1) - math.log(0.001)) + math.log(0.001)
        ).clamp(min=1e-4)
        inv_dt = dt + torch.log(-torch.expm1(-dt)) # inverse softplus
        with torch.no_grad():
            self.dt_proj.bias.copy_(inv_dt)

        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

        a = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        # Add small variance so channels aren't perfectly identical at initialization
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
        # A_log is (d_inner, d_state)
        # a should be (d_inner, d_state)
        a = -torch.exp(self.A_log).to(dtype=u.dtype, device=u.device)
        d = self.D.to(dtype=u.dtype, device=u.device)

        # Initial state should be float32 for stability
        state = torch.zeros(
            (batch_size, self.d_inner, self.d_state),
            device=u.device,
            dtype=torch.float32
        )
        outputs = []

        # Precompute discretization:
        # delta is (B, L, d_inner)
        # b_term is (B, L, d_state)
        # c_term is (B, L, d_state)

        # Vectorized expansion for the loop
        # delta.unsqueeze(-1) is (B, L, d_inner, 1)
        # a.unsqueeze(0).unsqueeze(0) is (1, 1, d_inner, d_state)
        # delta_a is (B, L, d_inner, d_state)
        delta_a = torch.exp(delta.unsqueeze(-1) * a.unsqueeze(0).unsqueeze(0))

        # delta_b_u: (B, L, d_inner, d_state)
        # delta is (B, L, d_inner)
        # b_term is (B, L, d_state)
        # u is (B, L, d_inner)
        # We want (delta * u) @ b_term? No, Mamba logic is:
        # B_bar = delta * B
        # state = A_bar * state + B_bar * u
        # Which is: state = exp(delta * A) * state + (delta * B * u)

        delta_u = delta * u # (B, L, d_inner)
        # delta_u.unsqueeze(-1) * b_term.unsqueeze(2) -> (B, L, d_inner, d_state)
        delta_b_u = delta_u.unsqueeze(-1) * b_term.unsqueeze(2)

        # Ensure all are float32 during scan for stability
        delta_a = delta_a.to(torch.float32)
        delta_b_u = delta_b_u.to(torch.float32)
        c_term = c_term.to(torch.float32)
        u_f32 = u.to(torch.float32)
        d_f32 = d.to(torch.float32)

        for t in range(seq_len):
            state = delta_a[:, t] * state + delta_b_u[:, t]
            # y_t = state @ C + D*u
            # state is (B, d_inner, d_state)
            # c_term[:, t] is (B, d_state)
            # We need (B, d_inner)
            y_t = (state * c_term[:, t].unsqueeze(1)).sum(dim=-1) + d_f32 * u_f32[:, t]
            outputs.append(y_t)

        return torch.stack(outputs, dim=1).to(u.dtype)
