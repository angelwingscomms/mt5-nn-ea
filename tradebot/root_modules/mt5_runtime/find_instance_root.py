from __future__ import annotations

from .shared import *  # noqa: F401,F403

def find_instance_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if is_instance_root(candidate):
            return candidate
    return None
