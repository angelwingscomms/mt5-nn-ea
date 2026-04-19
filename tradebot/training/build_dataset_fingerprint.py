from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


def build_dataset_fingerprint(
    csv_path: Path, *, chunk_size: int = 1024 * 1024
) -> dict[str, str | int]:
    """Return stable metadata for the exact CSV used during training."""

    resolved_path = csv_path.resolve()
    stat = resolved_path.stat()
    digest = sha256()
    with resolved_path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return {
        "path": resolved_path.as_posix(),
        "size_bytes": int(stat.st_size),
        "modified_utc": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "sha256": digest.hexdigest(),
    }
