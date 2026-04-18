from __future__ import annotations

from .shared import *  # noqa: F401,F403

def wait_for_tester_completion(main_log_path: Path, offset: int, timeout_seconds: int) -> str:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        tester_text = read_appended_text(main_log_path, offset)
        tester_text_lower = tester_text.lower()
        if (
            "automatical testing finished" in tester_text_lower
            or "thread finished" in tester_text_lower
            or "stop testing" in tester_text_lower
        ):
            return tester_text
        time.sleep(1.0)
    raise TimeoutError(f"Timed out waiting for tester completion in {main_log_path}.")
