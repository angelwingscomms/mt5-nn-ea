from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _candidate_wineprefixes() -> list[Path]:
    candidates: list[Path] = []
    env_wineprefix = os.environ.get("WINEPREFIX", "").strip()
    if env_wineprefix:
        _append_unique(candidates, Path(env_wineprefix))

    for candidate in SCRIPT_DIR.parents:
        if candidate.name.startswith("drive_") and candidate.parent.name in {".wine", ".mt5"}:
            _append_unique(candidates, candidate.parent)

    _append_unique(candidates, Path.home() / ".wine")
    _append_unique(candidates, Path.home() / ".mt5")
    return [candidate for candidate in candidates if candidate.exists()]
