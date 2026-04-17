from __future__ import annotations

from .shared import *  # noqa: F401,F403

def build_metaeditor_compile_command(
    runtime: Mt5RuntimePaths,
    source_path: Path,
) -> list[str]:
    source_value = to_windows_path(runtime, source_path) if runtime.use_wine else str(source_path)
    command = [
        str(runtime.metaeditor_path),
        f'/compile:"{source_value}"',
        "/log",
    ]
    if runtime.portable_mode:
        command.append("/portable")
    if runtime.use_wine:
        return ["wine", *command]
    return command
