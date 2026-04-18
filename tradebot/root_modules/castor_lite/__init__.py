"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import CastorTemporalBlock as _module_0
from .CastorTemporalBlock import CastorTemporalBlock
from . import CastorClassifier as _module_1
from .CastorClassifier import CastorClassifier

_MODULES = [
    _module_0,
    _module_1,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)



__all__ = [
    "CastorClassifier",
    "CastorTemporalBlock",
]
