"""Compact Castor-style classifier used by the training pipeline."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from tradebot.models.sequence import SequenceInstanceNorm, SequenceMultiAttentionHead
from tradebot.root_modules.mamba_lite import CausalDepthwiseConv1d, RMSNorm
