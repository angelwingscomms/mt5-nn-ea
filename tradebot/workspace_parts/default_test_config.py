from __future__ import annotations

from .shared import *  # noqa: F401,F403

def default_test_config(symbol: str) -> dict[str, int | float | str]:
    """Return the default tester settings used when no JSON exists yet."""

    return {
        "month": "",
        "from_date": "",
        "to_date": "",
        "symbol": symbol,
        "deposit": 10000.0,
        "currency": "USD",
        "leverage": "1:2000",
        "timeout_seconds": 600,
        "retries": 1,
    }
