from __future__ import annotations

from .shared import *  # noqa: F401,F403

def sync_directory_contents(source_dir: Path, destination_dir: Path) -> None:
    """Replace one directory tree with another."""

    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)
