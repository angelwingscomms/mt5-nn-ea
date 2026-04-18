from __future__ import annotations

from .shared import *  # noqa: F401,F403

def runtime_env(runtime: Mt5RuntimePaths) -> dict[str, str]:
    env = os.environ.copy()
    if runtime.use_wine and runtime.wineprefix is not None:
        env["WINEPREFIX"] = str(runtime.wineprefix)
    return env
