from __future__ import annotations

from .shared import *  # noqa: F401,F403

def read_appended_text(path: Path, offset: int) -> str:
    if not path.exists():
        return ""
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read()
    for encoding in ("utf-16", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")
