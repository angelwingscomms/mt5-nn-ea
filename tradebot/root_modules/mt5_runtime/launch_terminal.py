from __future__ import annotations

from .shared import *  # noqa: F401,F403

def launch_terminal(
    runtime: Mt5RuntimePaths,
    config_path: Path,
    timeout_seconds: int | None = None,
    detach: bool = False,
    stop_existing: bool = False,
) -> subprocess.CompletedProcess[str] | subprocess.Popen[str]:
    if stop_existing:
        stop_terminal_best_effort(runtime)

    command = build_terminal_command(runtime, config_path)
    env = runtime_env(runtime)
    if detach:
        popen_kwargs: dict[str, object] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "env": env,
            "text": True,
        }
        if runtime.host_platform == "windows":
            creation_flags = 0
            creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            popen_kwargs["creationflags"] = creation_flags
        else:
            popen_kwargs["start_new_session"] = True
        return subprocess.Popen(command, **popen_kwargs)

    run_kwargs: dict[str, object] = {
        "check": False,
        "capture_output": True,
        "text": True,
        "env": env,
    }
    if timeout_seconds is not None:
        run_kwargs["timeout"] = max(timeout_seconds + 60, 120)
    return subprocess.run(command, **run_kwargs)
