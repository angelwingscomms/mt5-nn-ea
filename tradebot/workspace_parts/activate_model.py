from __future__ import annotations

from .shared import *  # noqa: F401,F403

def activate_model(model_dir: Path) -> None:
    """Update the local `live.mq5` source to reference an archived model."""

    if not model_onnx_path(model_dir).exists():
        raise FileNotFoundError(f"Archived ONNX file not found: {model_onnx_path(model_dir)}")
    if not model_config_path(model_dir).exists():
        raise FileNotFoundError(f"Archived config file not found: {model_config_path(model_dir)}")
    set_live_model_reference(model_dir)
    diagnostics_dir = model_diagnostics_dir(model_dir)
    if diagnostics_dir.exists():
        sync_directory_contents(diagnostics_dir, ACTIVE_DIAGNOSTICS_DIR)
