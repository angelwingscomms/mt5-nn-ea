from __future__ import annotations

from .shared import *  # noqa: F401,F403

def default_linux_wineprefix() -> Path | None:
    candidates = _candidate_wineprefixes()
    return candidates[0] if candidates else None
