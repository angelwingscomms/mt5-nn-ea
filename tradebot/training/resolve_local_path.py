from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_local_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[2] / path
