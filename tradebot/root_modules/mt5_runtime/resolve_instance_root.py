from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_instance_root(instance_root_override: str = "") -> Path:
    candidates = _candidate_instance_roots(instance_root_override)
    if not candidates:
        raise FileNotFoundError(
            "Could not locate a MetaTrader 5 data folder. Pass --instance-root or set MT5_INSTANCE_ROOT/"
            "MQL5_DATA_FOLDER_PATH."
        )
    return max(candidates, key=_path_score)
