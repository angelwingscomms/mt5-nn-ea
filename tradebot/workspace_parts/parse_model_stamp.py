from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_model_stamp(folder_name: str) -> datetime:
    """Extract the timestamp from either new or legacy model folder names."""

    match = MODEL_STAMP_PREFIX_PATTERN.match(folder_name)
    if match:
        parsed = _try_parse_model_stamp_text(match.group("stamp"))
        if parsed is not None:
            return parsed

    match = MODEL_STAMP_SUFFIX_PATTERN.search(folder_name)
    if match:
        parsed = _try_parse_model_stamp_text(match.group("stamp"))
        if parsed is not None:
            return parsed

    parsed = _try_parse_model_stamp_text(folder_name)
    if parsed is not None:
        return parsed

    raise ValueError(
        "Model folders must contain a training stamp such as "
        "`03_04_2026-06_45__00-my-model` or `my-model-03_04_2026-06_45__00-fail`."
    )
