from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


COLLECTIONS = {
    "verticals": "vertical",
    "units": "unit",
    "types": "type",
    "operations": "operation",
    "surfaces": "surface",
    "stores": "store",
    "flows": "flow",
}

VERIFY_COLLECTIONS = {
    "startup": "verification",
    "surfaces": "verification",
    "flows": "verification",
}


@dataclass
class ForgeSchema:
    root: Path
    schema_version: str
    system: dict[str, Any]
    bootstrap: dict[str, Any]
    build_policy: dict[str, Any]
    collections: dict[str, list[dict[str, Any]]]
    verification: dict[str, list[dict[str, Any]]]
    promotion_gates: dict[str, Any]

    def all_objects(self) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = [
            {"kind": "system", **self.system},
            {"kind": "bootstrap", **self.bootstrap},
            {"kind": "build_policy", **self.build_policy},
        ]
        for kind, items in self.collections.items():
            for item in items:
                objects.append({"kind": COLLECTIONS[kind], **item})
        for _, items in self.verification.items():
            for item in items:
                objects.append({"kind": "verification", **item})
        return objects

    def index_by_id(self) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for item in self.all_objects():
            item_id = item.get("id")
            if item_id:
                indexed[item_id] = item
        return indexed


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def _unwrap_singleton(path: Path, key: str) -> dict[str, Any]:
    loaded = _read_yaml(path)
    if key in loaded and isinstance(loaded[key], dict):
        return loaded[key]
    return loaded


def _read_collection(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        items.append(_read_yaml(path))
    return items


def _normalize_type_refs(value: Any, singular_key: str | None = None) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, dict) and singular_key:
        inner = value.get(singular_key)
        if isinstance(inner, str):
            return [item.strip() for item in inner.split(",") if item.strip()]
    return []


def _normalize_operation(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized["inputs"] = _normalize_type_refs(normalized.get("inputs"))
    if not normalized["inputs"]:
        normalized["inputs"] = _normalize_type_refs(normalized.get("input"), "type")
    normalized["outputs"] = _normalize_type_refs(normalized.get("outputs"))
    if not normalized["outputs"]:
        normalized["outputs"] = _normalize_type_refs(normalized.get("output"), "type")
    normalized["referenced_types"] = _normalize_type_refs(normalized.get("referenced_types"))
    return normalized


def load_schema(root: Path) -> ForgeSchema:
    system_file = root / "system.yaml"
    bootstrap_file = root / "bootstrap.yaml"
    build_policy_file = root / "build_policy.yaml"

    system = _unwrap_singleton(system_file, "system")
    bootstrap = _unwrap_singleton(bootstrap_file, "bootstrap")
    build_policy = _unwrap_singleton(build_policy_file, "build_policy")
    schema_version = system.pop("schema_version", None)

    if not schema_version:
        root_marker = root / "schema.yaml"
        if root_marker.exists():
            schema_version = _read_yaml(root_marker).get("schema_version")
    if not schema_version:
        schema_version = "forge.v2"

    collections = {name: _read_collection(root / name) for name in COLLECTIONS}
    collections["operations"] = [_normalize_operation(item) for item in collections["operations"]]
    verification_root = root / "verification"
    verification = {
        name: _read_collection(verification_root / name) for name in VERIFY_COLLECTIONS
    }
    promotion_gates_file = verification_root / "promotion_gates.yaml"
    promotion_gates = _read_yaml(promotion_gates_file) if promotion_gates_file.exists() else {}

    return ForgeSchema(
        root=root,
        schema_version=schema_version,
        system=system,
        bootstrap=bootstrap,
        build_policy=build_policy,
        collections=collections,
        verification=verification,
        promotion_gates=promotion_gates,
    )


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
