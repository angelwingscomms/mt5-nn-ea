"""Split implementation package."""
from __future__ import annotations

from .shared import *  # noqa: F401,F403
from . import Mt5RuntimePaths as _module_0
from .Mt5RuntimePaths import Mt5RuntimePaths
from . import host_platform_name as _module_1
from .host_platform_name import host_platform_name
from . import _candidate_wineprefixes as _module_2
from ._candidate_wineprefixes import _candidate_wineprefixes
from . import default_linux_install_dirs as _module_3
from .default_linux_install_dirs import default_linux_install_dirs
from . import default_linux_wineprefix as _module_4
from .default_linux_wineprefix import default_linux_wineprefix
from . import is_instance_root as _module_5
from .is_instance_root import is_instance_root
from . import find_instance_root as _module_6
from .find_instance_root import find_instance_root
from . import read_text_best_effort as _module_7
from .read_text_best_effort import read_text_best_effort
from . import _append_unique as _module_8
from ._append_unique import _append_unique
from . import _existing_candidates as _module_9
from ._existing_candidates import _existing_candidates
from . import _first_existing as _module_10
from ._first_existing import _first_existing
from . import _path_score as _module_11
from ._path_score import _path_score
from . import _candidate_instance_roots as _module_12
from ._candidate_instance_roots import _candidate_instance_roots
from . import resolve_instance_root as _module_13
from .resolve_instance_root import resolve_instance_root
from . import _resolve_explicit_existing_path as _module_14
from ._resolve_explicit_existing_path import _resolve_explicit_existing_path
from . import resolve_terminal_path as _module_15
from .resolve_terminal_path import resolve_terminal_path
from . import resolve_metaeditor_path as _module_16
from .resolve_metaeditor_path import resolve_metaeditor_path
from . import resolve_mt5_runtime as _module_17
from .resolve_mt5_runtime import resolve_mt5_runtime
from . import ensure_runtime_dirs as _module_18
from .ensure_runtime_dirs import ensure_runtime_dirs
from . import iter_agent_log_paths as _module_19
from .iter_agent_log_paths import iter_agent_log_paths
from . import _manual_wine_path as _module_20
from ._manual_wine_path import _manual_wine_path
from . import to_windows_path as _module_21
from .to_windows_path import to_windows_path
from . import runtime_env as _module_22
from .runtime_env import runtime_env
from . import build_terminal_command as _module_23
from .build_terminal_command import build_terminal_command
from . import build_metaeditor_compile_command as _module_24
from .build_metaeditor_compile_command import build_metaeditor_compile_command
from . import stop_terminal_best_effort as _module_25
from .stop_terminal_best_effort import stop_terminal_best_effort
from . import launch_terminal as _module_26
from .launch_terminal import launch_terminal

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
    _module_17,
    _module_18,
    _module_19,
    _module_20,
    _module_21,
    _module_22,
    _module_23,
    _module_24,
    _module_25,
    _module_26,
]
_PACKAGE_GLOBALS = globals()
for _module in _MODULES:
    _module.__dict__.update(_PACKAGE_GLOBALS)
