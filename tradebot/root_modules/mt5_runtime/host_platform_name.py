from __future__ import annotations

from .shared import *  # noqa: F401,F403

def host_platform_name() -> str:
    system_name = platform.system().lower()
    if system_name.startswith("win"):
        return "windows"
    if system_name == "linux":
        return "linux"
    if system_name == "darwin":
        raise EnvironmentError("MetaTrader automation is not supported on macOS. Use Windows or Linux with Wine.")
    raise EnvironmentError(f"Unsupported operating system: {platform.system()}")
