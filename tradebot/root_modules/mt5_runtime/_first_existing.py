from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path.expanduser().resolve()
    return None
