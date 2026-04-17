from __future__ import annotations

from .shared import *  # noqa: F401,F403

def format_model_dir_name(
    *,
    value: datetime | None = None,
    name: str = "",
    failed_quality_gate: bool = False,
    symbol: str = "",
) -> str:
    """Return a canonical, resource-safe `<stamp>-<name>` model folder name."""

    stamp = format_model_stamp(value)
    suffix = sanitize_model_name(name)
    if symbol:
        max_length = _max_model_dir_name_length(symbol)
        max_suffix_length = max_length - len(stamp)
        if suffix:
            max_suffix_length -= 1
        if max_suffix_length < len(suffix):
            suffix = suffix[: max(0, max_suffix_length)].rstrip("._-")
    folder_name = f"{stamp}-{suffix}" if suffix else stamp
    if failed_quality_gate and (not symbol or len(folder_name) + len("-fail") <= _max_model_dir_name_length(symbol)):
        folder_name += "-fail"
    return folder_name
