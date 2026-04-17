from __future__ import annotations

from .shared import *  # noqa: F401,F403

def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[np.ndarray, np.ndarray]:
    model.eval()
    logits_list: list[np.ndarray] = []
    labels_list: list[np.ndarray] = []
    log.info("evaluate_model: starting - %d batches", len(loader))
    with torch.no_grad():
        for batch_idx, (xb, yb) in enumerate(loader):
            if batch_idx % 100 == 0:
                log.info("evaluate_model: batch %d/%d", batch_idx, len(loader))
            logits_list.append(model(xb.to(device)).cpu().numpy())
            labels_list.append(yb.numpy())
    log.info("evaluate_model: done - concatenating %d arrays", len(logits_list))
    result = np.concatenate(logits_list, axis=0), np.concatenate(labels_list, axis=0)
    log.info("evaluate_model: result shapes - logits=%s, labels=%s", result[0].shape, result[1].shape)
    return result
