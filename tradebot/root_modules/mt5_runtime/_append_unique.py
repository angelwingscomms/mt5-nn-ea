from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _append_unique(paths: list[Path], candidate: Path | None) -> None:
    if candidate is None:
        return
    normalized = candidate.expanduser().resolve()
    if normalized not in paths:
        paths.append(normalized)
