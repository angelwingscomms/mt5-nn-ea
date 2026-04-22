from __future__ import annotations

from .shared import *  # noqa: F401,F403

def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    with torch.no_grad():
        for batch_idx, (xb, yb) in enumerate(loader):
            logits_list.append(model(xb.to(device)).cpu().numpy())
            labels_list.append(yb.numpy())
    return np.concatenate(logits_list, axis=0), np.concatenate(labels_list, axis=0)
