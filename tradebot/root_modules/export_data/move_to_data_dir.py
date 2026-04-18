from __future__ import annotations

from .shared import *  # noqa: F401,F403

def move_to_data_dir(symbol: str, csv_path: Path) -> Path:
    symbol_dir = OUTPUT_DIR / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    dest_path = symbol_dir / "ticks.csv"

    print(f"[INFO] Moving {csv_path.name} to {dest_path}...")
    shutil.move(str(csv_path), str(dest_path))
    file_size_mb = dest_path.stat().st_size / (1024 * 1024)
    print(f"[INFO] Successfully moved file ({file_size_mb:.2f} MB)")
    print(f"[INFO] Output: {dest_path}")
    return dest_path
