from __future__ import annotations

from .shared import *  # noqa: F401,F403

def ensure_runtime_dirs(runtime: Mt5RuntimePaths) -> None:
    for path in (
        runtime.expert_dir,
        runtime.files_dir,
        runtime.presets_dir,
        runtime.tester_profile_dir,
        runtime.tester_dir,
        runtime.terminal_log_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
