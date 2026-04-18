from __future__ import annotations

from .shared import *  # noqa: F401,F403

def default_linux_install_dirs() -> list[Path]:
    install_dirs: list[Path] = []
    for wineprefix in _candidate_wineprefixes():
        _append_unique(install_dirs, wineprefix / "drive_c" / "Program Files" / "MetaTrader 5")
    return install_dirs
