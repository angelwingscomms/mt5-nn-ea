"""MiniRocket feature transforms plus lightweight classifier/export wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn


KERNEL_INDICES = np.asarray(list(combinations(range(9), 3)), dtype=np.int64)
BASE_KERNELS = np.full((len(KERNEL_INDICES), 9), -1.0, dtype=np.float32)
for kernel_index, combo in enumerate(KERNEL_INDICES):
    BASE_KERNELS[kernel_index, combo] = 2.0
