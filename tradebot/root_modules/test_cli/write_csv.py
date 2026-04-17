from __future__ import annotations

from .shared import *  # noqa: F401,F403

def write_csv(path: Path, rows: list[BacktestResult]) -> None:
    fieldnames = list(BacktestResult.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
