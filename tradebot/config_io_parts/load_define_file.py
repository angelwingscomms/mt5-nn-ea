from __future__ import annotations

from .shared import *  # noqa: F401,F403

def load_define_file(path: Path) -> dict[str, Scalar]:
    """Load all `#define` entries from a config-style file."""

    values: dict[str, Scalar] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = DEFINE_PATTERN.match(line)
        if not match:
            continue
        name, raw_value = match.groups()
        values[name] = parse_define_value(raw_value, values)
    return values
