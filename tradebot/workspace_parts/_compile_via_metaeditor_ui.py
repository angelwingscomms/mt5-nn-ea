from __future__ import annotations

from .shared import *  # noqa: F401,F403

def _compile_via_metaeditor_ui(runtime: Mt5RuntimePaths) -> None:
    """Use the UI fallback that matches the current host platform."""

    if runtime.use_wine:
        _compile_via_metaeditor_ui_wine(runtime)
        return
    if runtime.host_platform == "windows":
        _compile_via_metaeditor_ui_windows(runtime)
        return
    raise RuntimeError("MetaEditor UI fallback is only supported on Windows or Linux/Wine.")
