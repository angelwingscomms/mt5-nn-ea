from __future__ import annotations

from .shared import *  # noqa: F401,F403

@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data: Path
    symbols: Path
    diagnostics: Path

    @classmethod
    def from_root(cls, root: Path | None = None) -> "ProjectPaths":
        if root is None:
            root = ROOT_DIR
        return cls(
            root=root,
            data=root / "data",
            symbols=root / "symbols",
            diagnostics=root / "diagnostics",
        )
