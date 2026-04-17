from __future__ import annotations

from .shared import *  # noqa: F401,F403

def get_language_tag(filename: str) -> str:
    """Get the markdown language tag based on file extension."""
    ext = Path(filename).suffix.lower()
    return LANG_MAP.get(ext, '')
