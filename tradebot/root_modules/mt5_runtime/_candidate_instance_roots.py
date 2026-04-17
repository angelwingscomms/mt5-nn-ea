from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _candidate_instance_roots(instance_root_override: str) -> list[Path]:
    candidates: list[Path] = []
    if instance_root_override:
        _append_unique(candidates, Path(instance_root_override))
        return candidates

    for env_name in ("MT5_INSTANCE_ROOT", "MQL5_DATA_FOLDER_PATH"):
        value = os.environ.get(env_name, "").strip()
        if value:
            _append_unique(candidates, Path(value))

    detected = find_instance_root(SCRIPT_DIR)
    _append_unique(candidates, detected)

    platform_name = host_platform_name()
    if platform_name == "linux":
        for install_dir in default_linux_install_dirs():
            _append_unique(candidates, install_dir)
    else:
        appdata_value = os.environ.get("APPDATA", "").strip()
        if appdata_value:
            terminal_data_root = Path(appdata_value).expanduser() / "MetaQuotes" / "Terminal"
            if terminal_data_root.exists():
                for child in terminal_data_root.iterdir():
                    if child.is_dir() and is_instance_root(child):
                        _append_unique(candidates, child)
        _append_unique(candidates, DEFAULT_WINDOWS_INSTALL_DIR)

    return [candidate for candidate in candidates if candidate.exists() and is_instance_root(candidate)]
