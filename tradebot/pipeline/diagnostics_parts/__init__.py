"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import DiagnosticsConfig as _module_0
from .DiagnosticsConfig import DiagnosticsConfig
from . import class_count_lines as _module_1
from .class_count_lines import class_count_lines
from . import confusion_matrix_df as _module_2
from .confusion_matrix_df import confusion_matrix_df
from . import summarize_numeric as _module_3
from .summarize_numeric import summarize_numeric
from . import format_metric as _module_4
from .format_metric import format_metric
from . import build_prediction_frame as _module_5
from .build_prediction_frame import build_prediction_frame
from . import write_diagnostics as _module_6
from .write_diagnostics import write_diagnostics

_MODULES = [
    _module_0,
    _module_1,
    _module_2,
    _module_3,
    _module_4,
    _module_5,
    _module_6,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
