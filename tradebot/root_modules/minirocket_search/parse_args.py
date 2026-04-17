from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quick MiniRocket sweep over ATR stop/target multipliers without touching archived/live model files."
    )
    parser.add_argument("--sl-values", type=str, default="0.54,0.72,1.0,1.5")
    parser.add_argument("--tp-values", type=str, default="0.12,0.18,0.27,0.36,0.54")
    parser.add_argument("--train-windows", type=int, default=12000)
    parser.add_argument("--eval-windows", type=int, default=2048)
    parser.add_argument("--minirocket-features", type=int, default=1024)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--min-selected-trades", type=int, default=12)
    parser.add_argument("--use-fixed-time-bars", action="store_true")
    parser.add_argument(
        "--output-csv",
        type=str,
        default=str(Path("diagnostics") / "minirocket_search_results.csv"),
    )
    return parser.parse_args()
