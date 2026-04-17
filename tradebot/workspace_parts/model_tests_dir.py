from __future__ import annotations

from .shared import *  # noqa: F401,F403

def model_tests_dir(model_dir: Path) -> Path:
    """Return the backtest-results directory for one archived model."""

    return model_dir / "tests"
