from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _existing_candidates(directory: Path, names: tuple[str, ...]) -> list[Path]:
    return [directory / name for name in names if (directory / name).exists()]
