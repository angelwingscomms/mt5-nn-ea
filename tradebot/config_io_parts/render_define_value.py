from __future__ import annotations

from .shared import *  # noqa: F401,F403

def render_define_value(value: Scalar) -> str:
    """Render a Python scalar back into a valid MQL `#define` literal."""

    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)
