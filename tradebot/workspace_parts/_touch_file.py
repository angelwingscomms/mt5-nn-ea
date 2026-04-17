from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _touch_file(path: Path) -> None:
    """Update the timestamp on a file so MetaEditor notices a changed source."""

    now = time.time()
    os.utime(path, (now, now))
