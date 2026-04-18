"""Stable float-array formatting for generated MQL config files."""

from __future__ import annotations

import numpy as np


def format_float_array(values: np.ndarray) -> str:
    return ", ".join(f"{float(v):.8f}f" for v in values)
