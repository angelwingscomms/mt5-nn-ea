"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import ProjectPaths as _module_0
from .ProjectPaths import ProjectPaths
from . import BarMode as _module_1
from .BarMode import BarMode

_MODULES = [
    _module_0,
    _module_1,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
