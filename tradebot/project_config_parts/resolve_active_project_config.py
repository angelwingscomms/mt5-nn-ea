from __future__ import annotations

from .shared import *  # noqa: F401,F403

def resolve_active_project_config(config_path: Path) -> ResolvedProjectConfig:
    """Load the root config plus any optional architecture-only overlay."""

    values = load_define_file(config_path)
    architecture_config_path = config_path_value(values, "ARCHITECTURE_CONFIG")
    if architecture_config_path is not None:
        architecture_values = load_define_file(architecture_config_path)
        values = {**values, **architecture_values}

    symbol = str(values.get("SYMBOL", "XAUUSD")).strip() or "XAUUSD"
    if not str(values.get("DATA_FILE", "")).strip():
        values["DATA_FILE"] = default_data_file(symbol)

    architecture = resolve_architecture(values)
    feature_columns = resolve_feature_columns(values, architecture=architecture)
    feature_profile = resolve_feature_profile(values, feature_columns)
    return ResolvedProjectConfig(
        config_path=config_path,
        architecture_config_path=architecture_config_path,
        values=values,
        architecture=architecture,
        feature_columns=feature_columns,
        feature_profile=feature_profile,
    )
