from __future__ import annotations

from .shared import *  # noqa: F401,F403

def runtime_script_dir(runtime) -> Path:
    return runtime.instance_root / "MQL5" / "Scripts" / PROJECT_DIR_NAME
