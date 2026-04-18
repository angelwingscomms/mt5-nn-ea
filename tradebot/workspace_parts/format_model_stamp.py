from __future__ import annotations

from .shared import *  # noqa: F401,F403

def format_model_stamp(value: datetime | None = None) -> str:
    """Format a model timestamp using the repo's stable folder naming style."""

    return (value or datetime.now()).strftime(DEFAULT_MODEL_STAMP_FORMAT)
