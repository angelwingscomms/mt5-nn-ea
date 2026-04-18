from __future__ import annotations

from .shared import *  # noqa: F401,F403

@torch.no_grad()
def transform_sequence_tokens(
    parameters: MiniRocketTransformParameters,
    sequences: np.ndarray,
    batch_size: int = 512,
    device: str | torch.device = "cpu",
) -> np.ndarray:
    extractor = MiniRocketFeatureExtractor(parameters=parameters).to(device)
    extractor.eval()
    features: list[np.ndarray] = []
    for start in range(0, len(sequences), batch_size):
        batch = torch.from_numpy(sequences[start : start + batch_size]).to(device)
        features.append(extractor.encode_tokens(batch).cpu().numpy())
    if not features:
        return np.empty((0, extractor.num_tokens, extractor.token_feature_dim), dtype=np.float32)
    return np.concatenate(features, axis=0).astype(np.float32, copy=False)
