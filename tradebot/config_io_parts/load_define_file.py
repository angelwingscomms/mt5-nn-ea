from __future__ import annotations

from pathlib import Path

from .parse_define_value import parse_define_value
from .shared import DEFINE_PATTERN, Scalar


def load_define_file(path: Path) -> dict[str, Scalar]:
    """Load all `#define` entries from a config file or directory.

    If path is a file, loads that single file.
    If path is a directory, recursively loads all .mqh files in alphabetical order,
    then all non-file/non-directory items (config files without extension).
    Directories are processed first in alphabetical order, then files.
    """
    if path.is_dir():
        return _load_config_dir(path)
    return _load_config_file(path)


def _load_config_dir(dir_path: Path) -> dict[str, Scalar]:
    """Recursively load all config entries from a directory."""
    result: dict[str, Scalar] = {}
    items = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
    for item in items:
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            result.update(_load_config_dir(item))
        else:
            result.update(_load_config_file(item))
    return result


def _load_config_file(path: Path) -> dict[str, Scalar]:
    """Load all `#define` entries from a single config file."""
    values: dict[str, Scalar] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = DEFINE_PATTERN.match(line)
        if not match:
            continue
        name, raw_value = match.groups()
        values[name] = parse_define_value(raw_value, values)
    return values
