"""Helpers for reading and resolving MQL-style config files.

The repo stores user-editable configuration in `.mqh`/`.config` files so the
same values can be consumed by Python training code and the MQL5 runtime.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

Scalar = bool | int | float | str

DEFINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\s*#define\s+([A-Z0-9_]+)\s+(.+?)\s*$")
SAFE_SYMBOL_PATTERN: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_.-]+")
