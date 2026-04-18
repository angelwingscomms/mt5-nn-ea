from __future__ import annotations

from .shared import *  # noqa: F401,F403

def latest_model_dir(symbol: str) -> Path:
    """Return the latest archived model that still has the required artifacts."""

    candidates = [
        candidate
        for candidate in iter_model_dirs(symbol)
        if model_onnx_path(candidate).exists() and model_config_path(candidate).exists()
    ]
    if not candidates:
        raise FileNotFoundError(f"No archived models found for symbol '{symbol}'.")
    return candidates[-1]
