"""MT5 runtime discovery and command-building helpers."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[3]
PROJECT_DIR_NAME = SCRIPT_DIR.name
DEFAULT_WINDOWS_INSTALL_DIR = Path(r"C:\Program Files\MetaTrader 5")
DEFAULT_WINDOWS_TERMINAL_PATH = DEFAULT_WINDOWS_INSTALL_DIR / "terminal64.exe"
DEFAULT_WINDOWS_METAEDITOR_PATH = DEFAULT_WINDOWS_INSTALL_DIR / "MetaEditor64.exe"
TERMINAL_EXECUTABLE_NAMES = ("terminal64.exe", "Terminal64.exe")
METAEDITOR_EXECUTABLE_NAMES = ("metaeditor64.exe", "MetaEditor64.exe")
METATESTER_EXECUTABLE_NAMES = ("metatester64.exe", "MetaTester64.exe")
