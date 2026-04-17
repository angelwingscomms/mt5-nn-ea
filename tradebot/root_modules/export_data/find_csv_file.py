from __future__ import annotations

from .shared import *  # noqa: F401,F403

def find_csv_file(files_dir: Path, output_file: str, max_wait: float) -> Path | None:
    start_time = time.time()
    csv_path = files_dir / output_file
    print(f"[INFO] Waiting for {csv_path}...")

    while time.time() - start_time < max_wait:
        if csv_path.exists():
            time.sleep(0.5)
            if csv_path.stat().st_size > 100:
                print(f"[INFO] Found: {csv_path}")
                return csv_path
        time.sleep(0.5)
    return None
