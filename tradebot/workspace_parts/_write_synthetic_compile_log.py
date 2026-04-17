from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _write_synthetic_compile_log(path: Path, message: str) -> None:
    """Write a small synthetic compile log when MetaEditor omits one."""

    path.write_text(
        "\n".join(
            [
                message,
                "Result: 0 errors, 0 warnings",
                "",
            ]
        ),
        encoding="utf-8",
    )
