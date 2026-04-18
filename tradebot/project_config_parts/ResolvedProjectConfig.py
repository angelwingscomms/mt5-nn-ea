from __future__ import annotations

from .shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ResolvedProjectConfig:
    """Fully resolved config values used by the Python pipeline."""

    config_path: Path
    architecture_config_path: Path | None
    values: dict[str, Scalar]
    architecture: str
    feature_columns: tuple[str, ...]
    feature_profile: str
