from __future__ import annotations

from .shared import *  # noqa: F401,F403

def sanitize_model_name(name: str) -> str:
    """Return a filesystem-safe model label."""

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return cleaned.strip("._-")
