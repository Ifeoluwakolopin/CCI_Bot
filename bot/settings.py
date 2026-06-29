import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


def _resolve_path(path: str | os.PathLike[str]) -> Path:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
    return config_path


def load_config() -> dict[str, Any]:
    config_path = _resolve_path(os.getenv("CONFIG_PATH", DEFAULT_CONFIG_PATH))
    with config_path.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def config_value(
    config: Mapping[str, Any], path: Sequence[str], default: Any = None
) -> Any:
    current: Any = config
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return default
        current = current[key]
    return current


def env_or_config(
    config: Mapping[str, Any],
    env_name: str,
    path: Sequence[str],
    default: Any = None,
) -> Any:
    value = os.getenv(env_name)
    if value not in (None, ""):
        return value
    return config_value(config, path, default)


def int_env_or_config(
    config: Mapping[str, Any],
    env_name: str,
    path: Sequence[str],
    default: int | None = None,
) -> int | None:
    value = env_or_config(config, env_name, path, default)
    if value in (None, ""):
        return default
    return int(value)


def list_env_or_config(
    config: Mapping[str, Any],
    env_name: str,
    path: Sequence[str],
    default: Sequence[str] | None = None,
) -> list[str]:
    value = env_or_config(config, env_name, path, default or [])
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if value is None:
        return []
    return list(value)
