from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def workbench_dir(forge_root: Path) -> Path:
    return forge_root / "workbench"


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)


def append_unique_items(existing: list[dict[str, Any]], items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    indexed = {item.get(key): item for item in existing if isinstance(item, dict)}
    for item in items:
        if isinstance(item, dict) and item.get(key) is not None:
            indexed[item[key]] = item
    return list(indexed.values())
