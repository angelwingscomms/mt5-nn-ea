from __future__ import annotations

from .shared import *  # noqa: F401,F403

def iter_agent_log_paths(runtime: Mt5RuntimePaths) -> list[Path]:
    if not runtime.tester_dir.exists():
        return []
    return sorted(runtime.tester_dir.glob("Agent-*/logs/*.log"))
