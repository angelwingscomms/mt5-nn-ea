from __future__ import annotations

from .shared import *  # noqa: F401,F403

def config_path_value(values: dict[str, Scalar], key: str) -> Path | None:
    """Resolve an optional repo-relative path from the config values."""

    raw = str(values.get(key, "")).strip()
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else ROOT_DIR / path
