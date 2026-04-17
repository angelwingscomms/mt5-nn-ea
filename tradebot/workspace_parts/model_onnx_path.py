from __future__ import annotations

from .shared import *  # noqa: F401,F403

def model_onnx_path(model_dir: Path) -> Path:
    """Return the ONNX path inside one archived model folder."""

    return model_dir / MODEL_FILE_NAME
