from __future__ import annotations

from .shared import *  # noqa: F401,F403

def set_live_model_reference(model_dir: Path, live_path: Path = LIVE_MQ5_PATH) -> None:
    """Point `live.mq5` at a specific archived model directory."""

    if not model_onnx_path(model_dir).exists():
        raise FileNotFoundError(f"Archived ONNX file not found: {model_onnx_path(model_dir)}")
    if not model_config_path(model_dir).exists():
        raise FileNotFoundError(f"Archived config file not found: {model_config_path(model_dir)}")

    text = live_path.read_text(encoding="utf-8")
    replacement_block = build_live_model_reference_block(model_dir)
    updated_text, replacements = LIVE_MODEL_BLOCK_PATTERN.subn(
        lambda _match: replacement_block,
        text,
        count=1,
    )
    if replacements != 1:
        raise ValueError(
            f"{live_path} is missing the active model reference markers "
            f"{LIVE_MODEL_BLOCK_BEGIN!r} / {LIVE_MODEL_BLOCK_END!r}."
        )
    live_path.write_text(updated_text, encoding="utf-8")
