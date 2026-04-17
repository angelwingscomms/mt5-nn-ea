from __future__ import annotations

from .shared import *  # noqa: F401,F403

def merged_test_config(args: argparse.Namespace, default_symbol: str, model_dir: Path) -> dict[str, int | float | str]:
    tests_dir = model_tests_dir(model_dir)
    config_path = ensure_default_test_config(tests_dir, symbol=default_symbol)
    base = load_test_config(config_path)
    symbol = args.symbol or str(base.get("symbol", default_symbol)) or default_symbol
    return {
        "month": args.month or str(base.get("month", "")),
        "from_date": args.from_date or str(base.get("from_date", "")),
        "to_date": args.to_date or str(base.get("to_date", "")),
        "symbol": symbol,
        "deposit": float(args.deposit if args.deposit is not None else base.get("deposit", 10000.0)),
        "currency": str(args.currency or base.get("currency", "USD")),
        "leverage": str(args.leverage or base.get("leverage", "1:2000")),
        "timeout_seconds": int(
            args.timeout_seconds if args.timeout_seconds is not None else base.get("timeout_seconds", 600)
        ),
        "retries": int(args.retries if args.retries is not None else base.get("retries", 1)),
    }
