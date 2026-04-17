from __future__ import annotations

from .shared import *  # noqa: F401,F403

def stop_terminal_best_effort(runtime: Mt5RuntimePaths) -> None:
    commands: list[list[str]]
    if runtime.use_wine:
        commands = [
            ["wine", "cmd", "/c", "taskkill", "/IM", "terminal64.exe", "/F"],
            ["pkill", "-f", "terminal64.exe"],
        ]
    else:
        commands = [["taskkill", "/IM", "terminal64.exe", "/F"]]

    for command in commands:
        try:
            subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                env=runtime_env(runtime),
            )
        except FileNotFoundError:
            continue
