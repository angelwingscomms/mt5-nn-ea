from __future__ import annotations

from .shared import *  # noqa: F401,F403

def ensure_default_test_config(tests_dir: Path, symbol: str) -> Path:
    """Ensure a model has a seed `backtest_config.json` file."""

    config_path = tests_dir / DEFAULT_TEST_CONFIG_NAME
    if not config_path.exists():
        symbol_default_path = symbol_backtest_config_path(symbol)
        if symbol_default_path.exists():
            config_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(symbol_default_path, config_path)
        else:
            write_test_config(config_path, default_test_config(symbol))
    return config_path
