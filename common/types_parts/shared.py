"""Shared type definitions and stubs for Python ↔ MQL5 interop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

Scalar = bool | int | float | str

ROOT_DIR: Final[Path] = Path(__file__).resolve().parents[2]

GOLD_CONTEXT_TICK_COLUMNS: Final[tuple[str, ...]] = (
    "usdx_bid",
    "usdjpy_bid",
)

LABEL_NAMES: Final[tuple[str, ...]] = ("HOLD", "BUY", "SELL")
LABEL_NAMES_BINARY: Final[tuple[str, ...]] = ("BUY", "SELL")
