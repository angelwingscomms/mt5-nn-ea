from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _try_parse_model_stamp_text(value: str) -> datetime | None:
    """Parse one of the accepted timestamp shapes used by archived models."""

    for stamp_format in MODEL_STAMP_FORMATS:
        try:
            return datetime.strptime(value, stamp_format)
        except ValueError:
            continue
    return None
