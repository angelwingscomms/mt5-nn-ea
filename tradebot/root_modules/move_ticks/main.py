"""Move achilles tick exports from the MT5 sandbox into the project area."""

from __future__ import annotations

import shutil
from pathlib import Path


TERMINAL_PATH = Path(
    r"C:\Users\edhog\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075"
)
SOURCE_FILE = TERMINAL_PATH / "MQL5" / "Files" / "fast" / "achilles_ticks.csv"
DEST_FILE = TERMINAL_PATH / "MQL5" / "Experts" / "nn" / "fast" / "achilles_ticks.csv"


def move_ticks_file() -> bool:
    """Move the ticks file from the MT5 sandbox to the project directory."""

    print("=" * 60)
    print("ACHILLES TICKS FILE MOVER")
    print("=" * 60)

    if not SOURCE_FILE.exists():
        print(f"ERROR: Source file not found: {SOURCE_FILE}")
        return False

    file_size = SOURCE_FILE.stat().st_size
    print(f"Source file: {SOURCE_FILE}")
    print(f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

    DEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nMoving to: {DEST_FILE}")

    try:
        shutil.copy2(SOURCE_FILE, DEST_FILE)
        print("File copied successfully")

        if DEST_FILE.exists() and DEST_FILE.stat().st_size == file_size:
            SOURCE_FILE.unlink()
            print("Source file deleted")
            print("=" * 60)
            print("SUCCESS: File moved to project directory")
            print("=" * 60)
            return True

        print("ERROR: Destination file size mismatch")
        return False
    except Exception as exc:
        print(f"ERROR: Failed to move file: {exc}")
        return False


def main() -> None:
    move_ticks_file()

