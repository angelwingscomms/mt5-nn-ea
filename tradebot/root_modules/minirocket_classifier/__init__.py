"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import MiniRocketTransformParameters as _module_0
from .MiniRocketTransformParameters import MiniRocketTransformParameters
from . import _fit_dilations as _module_1
from ._fit_dilations import _fit_dilations
from . import _quantiles as _module_2
from ._quantiles import _quantiles
from . import _sample_channel_combinations as _module_3
from ._sample_channel_combinations import _sample_channel_combinations
from . import _compute_same_padded_response as _module_4
from ._compute_same_padded_response import _compute_same_padded_response
from . import fit_minirocket as _module_5
from .fit_minirocket import fit_minirocket
from . import MiniRocketFeatureExtractor as _module_6
from .MiniRocketFeatureExtractor import MiniRocketFeatureExtractor
from . import MiniRocketMultiAttentionHead as _module_7
from .MiniRocketMultiAttentionHead import MiniRocketMultiAttentionHead
from . import MiniRocketAttentionBlock as _module_8
from .MiniRocketAttentionBlock import MiniRocketAttentionBlock
from . import MiniRocketClassifier as _module_9
from .MiniRocketClassifier import MiniRocketClassifier
from . import transform_sequences as _module_10
from .transform_sequences import transform_sequences
from . import transform_sequence_tokens as _module_11
from .transform_sequence_tokens import transform_sequence_tokens

_MODULES = [
    _module_0,
    _module_1,
    _module_2,
    _module_3,
    _module_4,
    _module_5,
    _module_6,
    _module_7,
    _module_8,
    _module_9,
    _module_10,
    _module_11,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)



__all__ = [
    "MiniRocketAttentionBlock",
    "MiniRocketClassifier",
    "MiniRocketFeatureExtractor",
    "MiniRocketMultiAttentionHead",
    "MiniRocketTransformParameters",
    "fit_minirocket",
    "transform_sequence_tokens",
    "transform_sequences",
]
