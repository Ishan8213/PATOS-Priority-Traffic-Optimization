import os
from collections.abc import Mapping
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(
    environment_variable: str,
    default_relative_path: str,
    environment: Mapping[str, str] | None = None,
) -> Path:
    values = os.environ if environment is None else environment
    configured_path = values.get(environment_variable)
    path = Path(configured_path).expanduser() if configured_path else Path(default_relative_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def display_video_enabled(environment: Mapping[str, str] | None = None) -> bool:
    values = os.environ if environment is None else environment
    configured_value = values.get("PATOS_DISPLAY_VIDEO")

    if configured_value is not None:
        normalized_value = configured_value.strip().lower()
        if normalized_value in {"1", "true", "yes", "on"}:
            return True
        if normalized_value in {"0", "false", "no", "off"}:
            return False
        raise ValueError(
            "PATOS_DISPLAY_VIDEO must be set to true/false, 1/0, yes/no, or on/off."
        )

    return os.name == "nt" or bool(values.get("DISPLAY") or values.get("WAYLAND_DISPLAY"))
