from __future__ import annotations

from .shared import *  # noqa: F401,F403

def run_script(runtime, symbol: str, profile: str) -> None:
    if not runtime.terminal_path.exists():
        raise FileNotFoundError(f"MT5 terminal not found: {runtime.terminal_path}")

    stop_terminal_best_effort(runtime)
    config_path = write_startup_config(symbol, profile=profile)
    command = build_terminal_command(runtime, config_path)
    print(f"[INFO] Launching MT5 with {profile_script_name(profile)}.mq5 for {symbol}...")
    print(f"[INFO] Command: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=runtime_env(runtime),
        text=True,
        start_new_session=(runtime.host_platform != "windows"),
    )
    print(f"[INFO] Terminal started (PID: {process.pid})")
