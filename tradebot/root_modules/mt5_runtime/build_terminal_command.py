from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_terminal_command(runtime: Mt5RuntimePaths, config_path: Path) -> list[str]:
    config_value = to_windows_path(runtime, config_path) if runtime.use_wine else str(config_path)
    config_arg = f"/config:{config_value}"
    command = [str(runtime.terminal_path), config_arg]
    if runtime.portable_mode:
        command.append("/portable")
    if runtime.use_wine:
        return ["wine", *command]
    return command
