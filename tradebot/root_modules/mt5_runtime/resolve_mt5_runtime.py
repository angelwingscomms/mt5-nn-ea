from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_mt5_runtime(
    instance_root_override: str = "",
    terminal_path_override: str = "",
    metaeditor_path_override: str = "",
) -> Mt5RuntimePaths:
    platform_name = host_platform_name()
    instance_root = resolve_instance_root(instance_root_override)
    terminal_path = resolve_terminal_path(instance_root, terminal_path_override)
    metaeditor_path = resolve_metaeditor_path(instance_root, terminal_path, metaeditor_path_override)
    wineprefix = default_linux_wineprefix() if platform_name == "linux" else None

    return Mt5RuntimePaths(
        host_platform=platform_name,
        use_wine=(platform_name == "linux"),
        wineprefix=wineprefix,
        instance_root=instance_root,
        terminal_path=terminal_path,
        metaeditor_path=metaeditor_path,
        expert_dir=instance_root / "MQL5" / "Experts" / PROJECT_DIR_NAME,
        files_dir=instance_root / "MQL5" / "Files",
        presets_dir=instance_root / "MQL5" / "Presets",
        tester_profile_dir=instance_root / "MQL5" / "Profiles" / "Tester",
        tester_dir=instance_root / "Tester",
        terminal_log_dir=instance_root / "Tester" / "logs",
        portable_mode=(terminal_path.parent.resolve() == instance_root.resolve()),
    )
