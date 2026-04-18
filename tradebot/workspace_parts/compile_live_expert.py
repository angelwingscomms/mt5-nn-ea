from __future__ import annotations

from .shared import *  # noqa: F401,F403

def compile_live_expert(runtime: Mt5RuntimePaths, model_dir: Path, skip_deployment: bool = False) -> Path:
    """Compile the live EA after deploying the selected archived model tree."""

    if not skip_deployment:
        deploy_active_model(runtime, model_dir=model_dir)
    runtime.deployed_compile_log.unlink(missing_ok=True)
    source_log_path = runtime.deployed_live_mq5.with_suffix(".log")
    source_log_path.unlink(missing_ok=True)
    previous_ex5_mtime = runtime.deployed_live_ex5.stat().st_mtime if runtime.deployed_live_ex5.exists() else 0.0
    _touch_file(runtime.deployed_live_mq5)
    command = build_metaeditor_compile_command(
        runtime=runtime,
        source_path=runtime.deployed_live_mq5,
    )
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=runtime_env(runtime),
    )
    if source_log_path.exists():
        shutil.copy2(source_log_path, runtime.deployed_compile_log)
    log_text = read_text_best_effort(runtime.deployed_compile_log) if runtime.deployed_compile_log.exists() else ""
    if not log_text and completed.stdout:
        log_text = completed.stdout

    result_match = COMPILE_RESULT_PATTERN.search(log_text)
    if result_match:
        errors = int(result_match.group(1))
        warnings = int(result_match.group(2))
        if errors > 0:
            raise RuntimeError(
                f"live.mq5 compile failed with {errors} errors and {warnings} warnings. "
                f"Check log at {runtime.deployed_compile_log}."
            )
        return runtime.deployed_compile_log

    for _ in range(10):
        if runtime.deployed_live_ex5.exists() and runtime.deployed_live_ex5.stat().st_mtime > previous_ex5_mtime:
            _write_synthetic_compile_log(
                runtime.deployed_compile_log,
                "MetaEditor updated live.ex5 without producing a dedicated CLI compile log.",
            )
            return runtime.deployed_compile_log
        time.sleep(0.5)

    fallback_message = None
    if completed.returncode != 0:
        fallback_message = (
            f"MetaEditor returned exit code {completed.returncode} without a usable compile log, "
            "so a UI fallback compile was used successfully."
        )
    try:
        _compile_via_metaeditor_ui(runtime)
    except RuntimeError as exc:
        if completed.returncode != 0:
            raise RuntimeError(
                f"MetaEditor returned exit code {completed.returncode} while compiling {runtime.deployed_live_mq5}.\n"
                f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}\n\n"
                f"UI fallback error:\n{exc}"
            ) from exc
        raise
    _write_synthetic_compile_log(
        runtime.deployed_compile_log,
        fallback_message or "MetaEditor CLI produced no usable compile status, so a UI fallback compile was used successfully.",
    )
    return runtime.deployed_compile_log
