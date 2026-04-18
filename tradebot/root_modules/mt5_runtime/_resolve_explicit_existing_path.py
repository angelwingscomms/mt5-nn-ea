from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _resolve_explicit_existing_path(path_str: str) -> Path | None:
    value = path_str.strip()
    if not value:
        return None

    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate.resolve()

    which_path = shutil.which(value)
    if which_path:
        return Path(which_path).resolve()

    raise FileNotFoundError(f"Path not found: {path_str}")
