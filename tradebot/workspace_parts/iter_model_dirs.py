from __future__ import annotations

from .shared import *  # noqa: F401,F403

def iter_model_dirs(symbol: str) -> list[Path]:
    """Return archived model folders ordered by training time."""

    root = symbol_models_dir(symbol)
    if not root.exists():
        return []

    model_dirs: list[tuple[datetime, Path]] = []
    for candidate in root.iterdir():
        if not candidate.is_dir():
            continue
        try:
            model_dirs.append((parse_model_stamp(candidate.name), candidate))
        except ValueError:
            continue
    return [path for _, path in sorted(model_dirs, key=lambda item: item[0])]
