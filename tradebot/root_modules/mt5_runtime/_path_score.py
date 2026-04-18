from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _path_score(candidate: Path) -> tuple[int, float]:
    score = 0
    if (candidate / "MQL5" / "Experts" / PROJECT_DIR_NAME).exists():
        score += 100
    if _first_existing(_existing_candidates(candidate, TERMINAL_EXECUTABLE_NAMES)):
        score += 50
    if (candidate / "origin.txt").exists():
        score += 10

    mtime = 0.0
    for probe in (candidate / "origin.txt", candidate / "MQL5", candidate / "Tester"):
        if probe.exists():
            mtime = max(mtime, probe.stat().st_mtime)
    return score, mtime
