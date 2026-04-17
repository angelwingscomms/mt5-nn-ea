from __future__ import annotations

from .shared import *  # noqa: F401,F403

def to_windows_path(runtime: Mt5RuntimePaths, path: Path) -> str:
    if not runtime.use_wine:
        return str(path)

    if shutil.which("winepath"):
        completed = subprocess.run(
            ["winepath", "-w", str(path)],
            capture_output=True,
            text=True,
            check=False,
            env=runtime_env(runtime),
        )
        converted = completed.stdout.strip()
        if completed.returncode == 0 and converted:
            return converted

    if runtime.wineprefix is None:
        raise EnvironmentError("Wine prefix is required for Linux MetaTrader runtime handling.")
    return _manual_wine_path(path, runtime.wineprefix)
