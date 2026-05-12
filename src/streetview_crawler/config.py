from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = project_root() / config_path
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["_config_path"] = str(config_path)
    data["_project_root"] = str(project_root())
    return data


def resolve_path(config: dict[str, Any], value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return Path(config["_project_root"]) / path

