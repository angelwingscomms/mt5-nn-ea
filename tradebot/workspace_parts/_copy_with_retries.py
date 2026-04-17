from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _copy_with_retries(source_path: Path, destination_path: Path, *, log: logging.Logger) -> None:
    """Copy one file while tolerating temporary MetaTrader file locks."""

    max_retries = 3
    retry_delay = 1.0
    if source_path.resolve() == destination_path.resolve():
        log.info("Skipping deployment copy because source and destination match: %s", source_path)
        return
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(max_retries):
        try:
            shutil.copy2(source_path, destination_path)
            return
        except PermissionError as exc:
            if attempt == max_retries - 1:
                error_msg = (
                    f"Could not deploy {source_path.name} after {max_retries} attempts (file locked by MetaTrader). "
                    "Close MetaTrader 5 and retry, or skip compilation."
                )
                log.error(error_msg)
                raise PermissionError(error_msg) from exc
            wait_time = retry_delay * (2**attempt)
            log.warning(
                "Failed to copy %s (attempt %d/%d), retrying in %.1fs...",
                source_path.name,
                attempt + 1,
                max_retries,
                wait_time,
            )
            time.sleep(wait_time)
