from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _resource_literal_for_relative_model_dir(relative_model_dir: Path) -> str:
    """Return a `#resource` path that obeys the MQL5 path rules."""

    literal = relative_model_dir.as_posix().replace("/", "\\\\")
    literal += "\\\\" + MODEL_FILE_NAME
    if "\\" in literal.replace("\\\\", ""):
        raise ValueError(f"Resource literal was not fully escaped for MQL5: {literal!r}")
    if len(literal) > RESOURCE_PATH_MAX_CHARS:
        raise ValueError(
            "The ONNX resource path is too long for MQL5. "
            "Use a shorter model name so the archive folder stays within the 63-character resource limit."
        )
    return literal
