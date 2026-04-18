from __future__ import annotations

from .shared import *  # noqa: F401,F403

class FocalLoss(nn.Module):
    def __init__(self, alpha: torch.Tensor | None = None, gamma: float = 2.0):
        super().__init__()
        if alpha is not None:
            self.register_buffer("alpha", alpha.to(torch.float32))
        else:
            self.register_buffer("alpha", None)
        self.gamma = float(gamma)

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        log_probs = torch.log_softmax(logits, dim=1)
        log_pt = log_probs.gather(1, targets.view(-1, 1)).squeeze(1)
        pt = log_pt.exp()
        focal_term = (1.0 - pt).pow(self.gamma)
        alpha_t = 1.0 if self.alpha is None else self.alpha[targets]
        loss = -alpha_t * focal_term * log_pt
        return loss.mean()
