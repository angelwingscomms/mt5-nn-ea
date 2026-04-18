"""Bar building and label generation for the training pipeline."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common.bars import build_primary_bar_ids, build_tick_bar_ids, build_time_bar_ids, compute_tick_signs, infer_point_size_from_ticks
from common.types import GOLD_CONTEXT_TICK_COLUMNS


log = logging.getLogger("nn")
