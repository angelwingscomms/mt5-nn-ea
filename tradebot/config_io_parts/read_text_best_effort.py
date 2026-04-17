from __future__ import annotations

from .shared import *  # noqa: F401,F403

def read_text_best_effort(path: Path) -> str:
    """Read text files that may be written as UTF-8, UTF-16, or cp1252."""

    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")
