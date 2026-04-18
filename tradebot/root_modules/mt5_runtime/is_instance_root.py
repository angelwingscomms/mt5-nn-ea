from __future__ import annotations

from .shared import *  # noqa: F401,F403

def is_instance_root(path: Path) -> bool:
    return (path / "MQL5").is_dir() and (path / "Tester").is_dir()
