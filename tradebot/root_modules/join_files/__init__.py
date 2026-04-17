"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import get_language_tag as _module_0
from .get_language_tag import get_language_tag
from . import main as _module_1
from .main import main

_MODULES = [
    _module_0,
    _module_1,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
