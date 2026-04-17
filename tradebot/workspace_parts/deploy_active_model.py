from __future__ import annotations

from .shared import *  # noqa: F401,F403

def deploy_active_model(runtime: Mt5RuntimePaths, model_dir: Path) -> None:
    """Copy the live source and referenced archived model into the MT5 runtime."""

    ensure_runtime_dirs(runtime)
    log = logging.getLogger(__name__)
    _copy_with_retries(LIVE_MQ5_PATH, runtime.deployed_live_mq5, log=log)

    relative_model_dir = model_dir.relative_to(ROOT_DIR)
    runtime_model_dir = runtime.expert_dir / relative_model_dir
    runtime_model_dir.mkdir(parents=True, exist_ok=True)
    _copy_with_retries(model_onnx_path(model_dir), runtime_model_dir / MODEL_FILE_NAME, log=log)
    _copy_with_retries(model_config_path(model_dir), runtime_model_dir / MODEL_CONFIG_NAME, log=log)
