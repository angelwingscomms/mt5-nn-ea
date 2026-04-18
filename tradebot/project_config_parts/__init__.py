"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import ResolvedProjectConfig as _module_0
from .ResolvedProjectConfig import ResolvedProjectConfig
from . import resolve_architecture as _module_1
from .resolve_architecture import resolve_architecture
from . import _feature_enabled as _module_2
from ._feature_enabled import _feature_enabled
from . import _minimal_feature_enabled as _module_3
from ._minimal_feature_enabled import _minimal_feature_enabled
from . import resolve_feature_columns as _module_4
from .resolve_feature_columns import resolve_feature_columns
from . import resolve_feature_profile as _module_5
from .resolve_feature_profile import resolve_feature_profile
from . import config_path_value as _module_6
from .config_path_value import config_path_value
from . import default_data_file as _module_7
from .default_data_file import default_data_file
from . import resolve_active_project_config as _module_8
from .resolve_active_project_config import resolve_active_project_config

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
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)



__all__ = [
    "EXTRA_FEATURE_COLUMNS",
    "GOLD_CONTEXT_FEATURE_COLUMNS",
    "MAIN_FEATURE_COLUMNS",
    "MINIMAL_FEATURE_COLUMNS",
    "ResolvedProjectConfig",
    "config_path_value",
    "default_data_file",
    "feature_macro_name",
    "feature_switch_name",
    "max_feature_lookback",
    "minimal_feature_switch_name",
    "resolve_active_project_config",
    "resolve_architecture",
    "resolve_feature_columns",
    "resolve_feature_profile",
]
