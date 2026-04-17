from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_terminal_path(instance_root: Path, terminal_path_override: str = "") -> Path:
    explicit = _resolve_explicit_existing_path(terminal_path_override or os.environ.get("MT5_TERMINAL_PATH", ""))
    if explicit is not None:
        return explicit

    direct = _first_existing(_existing_candidates(instance_root, TERMINAL_EXECUTABLE_NAMES))
    if direct is not None:
        return direct

    origin_path = instance_root / "origin.txt"
    if origin_path.exists():
        install_dir = Path(read_text_best_effort(origin_path).strip()).expanduser()
        install_path = _first_existing(_existing_candidates(install_dir, TERMINAL_EXECUTABLE_NAMES))
        if install_path is not None:
            return install_path

    platform_name = host_platform_name()
    fallback_dirs = default_linux_install_dirs() if platform_name == "linux" else [DEFAULT_WINDOWS_INSTALL_DIR]
    for fallback_dir in fallback_dirs:
        fallback = _first_existing(_existing_candidates(fallback_dir, TERMINAL_EXECUTABLE_NAMES))
        if fallback is not None:
            return fallback

    raise FileNotFoundError(
        "Could not locate terminal64.exe. Pass --terminal-path or set MT5_TERMINAL_PATH."
    )
