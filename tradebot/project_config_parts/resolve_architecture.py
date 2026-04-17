from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_architecture(values: dict[str, Scalar]) -> str:
    """Return the configured model architecture string."""

    architecture = str(values.get("MODEL_ARCHITECTURE", "mamba")).strip().lower()
    if not architecture:
        raise ValueError("MODEL_ARCHITECTURE cannot be empty.")
    return architecture
