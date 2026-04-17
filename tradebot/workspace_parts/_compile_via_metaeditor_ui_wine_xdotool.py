from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _compile_via_metaeditor_ui_wine_xdotool(runtime: Mt5RuntimePaths) -> None:
    """Compile `live.mq5` via `wine start /unix` and xdotool key automation."""

    if shutil.which("xdotool") is None:
        raise RuntimeError("MetaEditor UI fallback on Linux/Wine requires xdotool.")

    subprocess.run(
        ["pkill", "-f", "MetaEditor64.exe"],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_env(runtime),
    )

    source_value = to_windows_path(runtime, runtime.deployed_live_mq5)
    previous_ex5_mtime = runtime.deployed_live_ex5.stat().st_mtime if runtime.deployed_live_ex5.exists() else 0.0
    previous_ex5_size = runtime.deployed_live_ex5.stat().st_size if runtime.deployed_live_ex5.exists() else -1
    completed = subprocess.run(
        ["wine", "start", "/unix", str(runtime.metaeditor_path), source_value],
        capture_output=True,
        text=True,
        check=False,
        env=runtime_env(runtime),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "MetaEditor UI fallback could not launch MetaEditor under Wine.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
        )

    deadline = time.time() + 30.0
    window_found = False
    while time.time() < deadline:
        search = subprocess.run(
            ["xdotool", "search", "--name", "MetaEditor", "getwindowname"],
            capture_output=True,
            text=True,
            check=False,
            env=runtime_env(runtime),
        )
        if search.returncode == 0 and search.stdout.strip():
            window_found = True
            break
        time.sleep(0.5)
    if not window_found:
        raise RuntimeError("MetaEditor window did not appear on the X11 display.")

    time.sleep(0.7)
    subprocess.run(
        ["xdotool", "search", "--name", "MetaEditor", "windowactivate", "--sync", "key", "--clearmodifiers", "F7"],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_env(runtime),
    )

    compile_deadline = time.time() + 60.0
    while time.time() < compile_deadline:
        if runtime.deployed_live_ex5.exists():
            ex5_stat = runtime.deployed_live_ex5.stat()
            if ex5_stat.st_mtime > previous_ex5_mtime or ex5_stat.st_size != previous_ex5_size:
                subprocess.run(
                    ["pkill", "-f", "MetaEditor64.exe"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=runtime_env(runtime),
                )
                return
        time.sleep(0.5)

    subprocess.run(
        ["pkill", "-f", "MetaEditor64.exe"],
        check=False,
        capture_output=True,
        text=True,
        env=runtime_env(runtime),
    )
    raise RuntimeError("MetaEditor UI fallback did not update live.ex5.")
