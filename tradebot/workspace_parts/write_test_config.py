from __future__ import annotations

from .shared import *  # noqa: F401,F403

def write_test_config(path: Path, data: dict[str, int | float | str]) -> None:
    """Write a stable, prettified backtest JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
