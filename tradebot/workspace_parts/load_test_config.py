from __future__ import annotations

from .shared import *  # noqa: F401,F403

def load_test_config(path: Path) -> dict[str, int | float | str]:
    """Load a backtest JSON file."""

    return json.loads(path.read_text(encoding="utf-8"))
