"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import RMSNorm as _module_0
from .RMSNorm import RMSNorm
from . import CausalDepthwiseConv1d as _module_1
from .CausalDepthwiseConv1d import CausalDepthwiseConv1d
from . import PortableMambaMixer as _module_2
from .PortableMambaMixer import PortableMambaMixer
from . import MambaLiteResidualBlock as _module_3
from .MambaLiteResidualBlock import MambaLiteResidualBlock
from . import MambaLiteClassifier as _module_4
from .MambaLiteClassifier import MambaLiteClassifier

_MODULES = [
    _module_0,
    _module_1,
    _module_2,
    _module_3,
    _module_4,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)



GoldMambaLiteClassifier = MambaLiteClassifier

__all__ = [
    "CausalDepthwiseConv1d",
    "GoldMambaLiteClassifier",
    "MambaLiteClassifier",
    "RMSNorm",
    "SequenceMultiAttentionHead",
]
