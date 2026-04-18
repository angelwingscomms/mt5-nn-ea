from __future__ import annotations

from .shared import *  # noqa: F401,F403

def deploy_script_files(runtime, shared_config_path: Path, profile: str) -> tuple[Path, Path]:
    script_dir = runtime_script_dir(runtime)
    script_dir.mkdir(parents=True, exist_ok=True)
    deployed_source = script_dir / f"{profile_script_name(profile)}.mq5"
    deployed_shared_config = script_dir / "config.mqh"
    source_path = DATA_PROFILE_SCRIPTS.get(profile, SCRIPT_DIR / "data.mq5")
    shutil.copy2(source_path, deployed_source)
    shutil.copy2(shared_config_path, deployed_shared_config)
    return deployed_source, deployed_shared_config
