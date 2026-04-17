"""Compact Castor-style classifier used by the training pipeline."""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn

from mamba_lite import CausalDepthwiseConv1d, RMSNorm
from sequence_models import SequenceInstanceNorm, SequenceMultiAttentionHead
