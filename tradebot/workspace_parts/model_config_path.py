from __future__ import annotations

from .shared import *  # noqa: F401,F403

def model_config_path(model_dir: Path) -> Path:
    """Return the single combined config file stored beside a model."""

    return model_dir / MODEL_CONFIG_NAME
