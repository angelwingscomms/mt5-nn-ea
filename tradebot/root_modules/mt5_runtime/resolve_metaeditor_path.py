from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_metaeditor_path(instance_root: Path, terminal_path: Path, metaeditor_path_override: str = "") -> Path:
    explicit = _resolve_explicit_existing_path(metaeditor_path_override or os.environ.get("MQL5_COMPILER_PATH", ""))
    if explicit is not None:
        return explicit

    for directory in (terminal_path.parent, instance_root):
        candidate = _first_existing(_existing_candidates(directory, METAEDITOR_EXECUTABLE_NAMES))
        if candidate is not None:
            return candidate

    platform_name = host_platform_name()
    fallback_dirs = default_linux_install_dirs() if platform_name == "linux" else [DEFAULT_WINDOWS_INSTALL_DIR]
    for fallback_dir in fallback_dirs:
        fallback = _first_existing(_existing_candidates(fallback_dir, METAEDITOR_EXECUTABLE_NAMES))
        if fallback is not None:
            return fallback

    raise FileNotFoundError(
        "Could not locate MetaEditor. Pass --metaeditor-path or set MQL5_COMPILER_PATH."
    )
