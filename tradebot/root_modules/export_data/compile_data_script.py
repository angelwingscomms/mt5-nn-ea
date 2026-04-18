from __future__ import annotations

from .shared import *  # noqa: F401,F403

def compile_data_script(runtime, shared_config_path: Path, profile: str) -> Path:
    source_path, deployed_shared_config = deploy_script_files(runtime, shared_config_path, profile=profile)
    target_path = source_path.with_suffix(".ex5")
    source_log_path = source_path.with_suffix(".log")
    COMPILE_LOG_PATH.unlink(missing_ok=True)
    source_log_path.unlink(missing_ok=True)

    newest_input_mtime = max(source_path.stat().st_mtime, deployed_shared_config.stat().st_mtime)
    if target_path.exists() and target_path.stat().st_mtime >= newest_input_mtime:
        return target_path

    command = build_metaeditor_compile_command(
        runtime=runtime,
        source_path=source_path,
    )
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=runtime_env(runtime),
    )
    if source_log_path.exists():
        shutil.copy2(source_log_path, COMPILE_LOG_PATH)

    if completed.returncode != 0 and not target_path.exists():
        log_text = read_text_best_effort(source_log_path) if source_log_path.exists() else ""
        raise RuntimeError(
            "MetaEditor failed to compile data.mq5.\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}\n\nlog:\n{log_text}"
        )
    deadline = time.time() + (60.0 if runtime.use_wine else 10.0)
    while time.time() < deadline:
        if target_path.exists() and target_path.stat().st_mtime >= newest_input_mtime:
            if source_log_path.exists() and not COMPILE_LOG_PATH.exists():
                shutil.copy2(source_log_path, COMPILE_LOG_PATH)
            return target_path
        time.sleep(0.5)
    log_text = read_text_best_effort(source_log_path) if source_log_path.exists() else ""
    if not target_path.exists():
        raise FileNotFoundError(
            f"Compiled script not found after MetaEditor run: {target_path}\n\n"
            f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}\n\nlog:\n{log_text}"
        )
    return target_path
