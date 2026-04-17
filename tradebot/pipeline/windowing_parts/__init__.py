"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import choose_evenly_spaced as _module_0
from .choose_evenly_spaced import choose_evenly_spaced
from . import maybe_cap_windows as _module_1
from .maybe_cap_windows import maybe_cap_windows
from . import build_segment_end_indices as _module_2
from .build_segment_end_indices import build_segment_end_indices
from . import build_windows as _module_3
from .build_windows import build_windows

_MODULES = [
    _module_0,
    _module_1,
    _module_2,
    _module_3,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
