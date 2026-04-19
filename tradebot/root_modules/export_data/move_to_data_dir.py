from __future__ import annotations

from .shared import *  # noqa: F401,F403


def _versioned_ticks_path(versions_dir: Path) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    candidate = versions_dir / f"ticks_{stamp}.csv"
    suffix = 1
    while candidate.exists():
        candidate = versions_dir / f"ticks_{stamp}_{suffix}.csv"
        suffix += 1
    return candidate


def move_to_data_dir(symbol: str, csv_path: Path) -> Path:
    symbol_dir = OUTPUT_DIR / symbol.strip().upper()
    symbol_dir.mkdir(parents=True, exist_ok=True)
    versions_dir = symbol_dir / "versions"
    versions_dir.mkdir(parents=True, exist_ok=True)
    version_path = _versioned_ticks_path(versions_dir)
    dest_path = symbol_dir / "ticks.csv"
    temp_path = symbol_dir / "ticks.csv.tmp"

    print(f"[INFO] Archiving {csv_path.name} to {version_path}...")
    shutil.move(str(csv_path), str(version_path))
    shutil.copy2(version_path, temp_path)
    temp_path.replace(dest_path)
    file_size_mb = dest_path.stat().st_size / (1024 * 1024)
    print(f"[INFO] Latest dataset refreshed atomically ({file_size_mb:.2f} MB)")
    print(f"[INFO] Output: {dest_path}")
    print(f"[INFO] Versioned snapshot: {version_path}")
    return dest_path
