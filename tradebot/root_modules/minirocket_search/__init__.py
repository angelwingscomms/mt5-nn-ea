"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import parse_float_list as _module_0
from .parse_float_list import parse_float_list
from . import parse_args as _module_1
from .parse_args import parse_args
from . import train_once as _module_2
from .train_once import train_once
from . import main as _module_3
from .main import main

_MODULES = [
    _module_0,
    _module_1,
    _module_2,
    _module_3,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
