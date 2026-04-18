from __future__ import annotations

from .shared import *  # noqa: F401,F403

def write_startup_config(symbol: str, profile: str) -> Path:
    STARTUP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    script_name = profile_script_name(profile)
    startup_config_path = STARTUP_CONFIG_DIR / f"{symbol.lower()}_{script_name}_export.ini"
    startup_config_path.write_text(
        "\n".join(
            [
                "[StartUp]",
                f"Script={PROJECT_DIR_NAME}\\{script_name}",
                f"Symbol={symbol}",
                "Period=M1",
                "ShutdownTerminal=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return startup_config_path
