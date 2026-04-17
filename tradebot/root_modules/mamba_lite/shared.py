"""Compact Mamba-inspired classifier used by the training pipeline."""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn
from tradebot.models.sequence import (
    SequenceInstanceNorm,
    SequenceMultiAttentionHead,
)
