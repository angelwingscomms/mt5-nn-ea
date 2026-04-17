from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test an archived model with the MT5 daily backtest pipeline.")
    parser.add_argument(
        "-i",
        "--symbol",
        type=str,
        default="",
        help="Symbol/model folder to test. Defaults to SYMBOL from config.mqh.",
    )
    parser.add_argument(
        "-r",
        "--revision",
        type=str,
        default="",
        help="Model training timestamp in DD_MM_YYYY-HH_MM__SS. If blank, test the latest model for the symbol.",
    )
    parser.add_argument("--month", type=str, default="", help="Month in YYYY-MM format. Defaults to config or last month.")
    parser.add_argument("--from-date", type=str, default="", help="Optional first day to run, in YYYY-MM-DD.")
    parser.add_argument("--to-date", type=str, default="", help="Optional last day to run, in YYYY-MM-DD.")
    parser.add_argument(
        "-d",
        "--day",
        nargs="?",
        const="",
        default=None,
        metavar="DDMMYY",
        help="Run a single-day backtest. Optionally pass DDMMYY; if omitted, it defaults to the previous day.",
    )
    parser.add_argument("--deposit", type=float, default=None, help="Initial deposit for each daily test.")
    parser.add_argument("--currency", type=str, default="", help="Deposit currency.")
    parser.add_argument("--leverage", type=str, default="", help="Tester leverage, for example 1:2000.")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="Maximum wait time per daily run.")
    parser.add_argument("--retries", type=int, default=None, help="Retries per day after a launch/logging failure.")
    parser.add_argument(
        "--metaeditor-path",
        type=str,
        default="",
        help="Optional explicit MetaEditor path. Leave blank to auto-detect on Windows or Linux/Wine.",
    )
    parser.add_argument(
        "--skip-live-compile",
        action="store_true",
        help="Skip compiling live.mq5 after activating the chosen archived model.",
    )
    parser.add_argument(
        "--instance-root",
        type=str,
        default="",
        help="Override the MT5 terminal data root that contains MQL5/ and Tester/.",
    )
    parser.add_argument(
        "--terminal-path",
        type=str,
        default="",
        help="Optional explicit path to terminal64.exe.",
    )
    return parser.parse_args()
