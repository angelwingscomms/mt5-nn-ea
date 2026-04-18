from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _manual_wine_path(path: Path, wineprefix: Path) -> str:
    normalized = path.expanduser().resolve(strict=False)
    try:
        relative = normalized.relative_to(wineprefix)
        drive_root = relative.parts[0]
        if drive_root.startswith("drive_") and len(drive_root) == 7:
            drive_letter = drive_root[-1].upper()
            remainder = relative.parts[1:]
            if not remainder:
                return f"{drive_letter}:\\"
            return f"{drive_letter}:\\" + "\\".join(remainder)
    except ValueError:
        pass

    drive_path = normalized.as_posix().lstrip("/").replace("/", "\\")
    return f"Z:\\{drive_path}"
