from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_model_dir(symbol: str, value: str = "") -> Path:
    """Resolve an explicit model folder name or fall back to the latest model."""

    if not value:
        return latest_model_dir(symbol)

    candidate = Path(value)
    model_dir = candidate if candidate.is_absolute() else symbol_models_dir(symbol) / value
    if not model_dir.exists():
        raise FileNotFoundError(f"Model folder not found: {model_dir}")
    if not model_dir.is_dir():
        raise NotADirectoryError(f"Model path is not a directory: {model_dir}")
    parse_model_stamp(model_dir.name)
    return model_dir
