"""Chronos-Bolt loading and wrapper helpers."""

from __future__ import annotations

from typing import Sequence

import torch
from torch import nn

DEFAULT_CHRONOS_BOLT_MODEL_ID = "amazon/chronos-bolt-tiny"
CHRONOS_BOLT_MODEL_IDS = (
    "amazon/chronos-bolt-tiny",
    "amazon/chronos-bolt-mini",
    "amazon/chronos-bolt-small",
    "amazon/chronos-bolt-base",
)
CHRONOS_BOLT_REQUIRED_FEATURES = (
    "ret1",
    "spread_rel",
    "atr_rel",
)
LOGIT_EPS = 1e-6
