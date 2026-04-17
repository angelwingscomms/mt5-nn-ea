from __future__ import annotations

from .shared import *  # noqa: F401,F403

def log_offsets(paths: list[Path]) -> dict[Path, int]:
    offsets: dict[Path, int] = {}
    for path in paths:
        if path.exists():
            offsets[path] = path.stat().st_size
        else:
            offsets[path] = 0
    return offsets
