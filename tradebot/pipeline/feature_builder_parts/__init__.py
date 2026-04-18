"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import FeatureEngineeringConfig as _module_0
from .FeatureEngineeringConfig import FeatureEngineeringConfig
from . import rolling_population_std as _module_1
from .rolling_population_std import rolling_population_std
from . import rolling_zscore as _module_2
from .rolling_zscore import rolling_zscore
from . import simple_rsi as _module_3
from .simple_rsi import simple_rsi
from . import true_range as _module_4
from .true_range import true_range
from . import wilder_atr as _module_5
from .wilder_atr import wilder_atr
from . import simple_atr as _module_6
from .simple_atr import simple_atr
from . import ema as _module_7
from .ema import ema
from . import macd_components as _module_8
from .macd_components import macd_components
from . import cci as _module_9
from .cci import cci
from . import willr as _module_10
from .willr import willr
from . import momentum as _module_11
from .momentum import momentum
from . import bollinger_width as _module_12
from .bollinger_width import bollinger_width
from . import _aux_context_required as _module_13
from ._aux_context_required import _aux_context_required
from . import _resolve_aux_series as _module_14
from ._resolve_aux_series import _resolve_aux_series
from . import compute_feature_frame as _module_15
from .compute_feature_frame import compute_feature_frame
from . import compute_features as _module_16
from .compute_features import compute_features

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
    _module_12,
    _module_13,
    _module_14,
    _module_15,
    _module_16,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
