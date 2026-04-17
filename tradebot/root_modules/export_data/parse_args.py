from __future__ import annotations

from .shared import *  # noqa: F401,F403

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export MT5 tick data into ./data/<SYMBOL>/ticks.csv.")
    parser.add_argument("--symbol", type=str, default="", help="Optional symbol preset to load from symbols/<symbol>/config.")
    parser.add_argument(
        "--profile",
        type=str,
        default="default",
        choices=sorted(DATA_PROFILE_SCRIPTS.keys()),
        help="Select the data export script profile (default or gold).",
    )
    parser.add_argument("--instance-root", type=str, default="", help="Optional explicit MT5 data root.")
    parser.add_argument("--terminal-path", type=str, default="", help="Optional explicit terminal64.exe path.")
    parser.add_argument("--metaeditor-path", type=str, default="", help="Optional explicit MetaEditor path.")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=60,
        help="Maximum time to wait for the exported CSV to appear in MQL5/Files.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=DEFAULT_OUTPUT_FILE,
        help="CSV filename written by data.mq5 inside MQL5/Files.",
    )
    return parser.parse_args()
