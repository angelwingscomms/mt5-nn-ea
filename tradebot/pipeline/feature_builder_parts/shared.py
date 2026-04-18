"""Feature engineering for the training pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import numpy as np
import pandas as pd

from common.features import GOLD_CONTEXT_FEATURE_COLUMNS, MAIN_GOLD_CONTEXT_FEATURE_COLUMNS
from tradebot.config_io import Scalar


EPS = 1e-10
