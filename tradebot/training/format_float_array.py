from __future__ import annotations

from .shared import *  # noqa: F401,F403

def format_float_array(values: np.ndarray) -> str:
    return ", ".join(f"{float(v):.8f}f" for v in values)
