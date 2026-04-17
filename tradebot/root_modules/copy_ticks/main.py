from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FILES_DIR = PROJECT_ROOT.parent / "Files"
GOLD_DIR = PROJECT_ROOT / "gold"
CSV_FILENAME = "gold_market_ticks.csv"


def main() -> None:
    source_path = FILES_DIR / CSV_FILENAME
    dest_path = GOLD_DIR / CSV_FILENAME

    print(f"[INFO] Looking for {CSV_FILENAME} in {FILES_DIR}...")
    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}")
        print("Make sure you have run data.mq5 in MT5 first.")
        return

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Copying to {dest_path}...")

    try:
        shutil.copy2(source_path, dest_path)
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"[INFO] Successfully copied {CSV_FILENAME} to gold directory.")
        print(f"[INFO] File size: {size_mb:.2f} MB")
    except Exception as exc:
        print(f"[ERROR] Failed to copy file: {exc}")

