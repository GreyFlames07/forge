from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT_SINGLETONS = {
    "system": "system.yaml",
    "runtime": "runtime.yaml",
    "early_state": "early_state.yaml",
    "deployment": "deployment.yaml",
}

COLLECTION_DIRS = {
    "high_level_flows": "high_level_flows",
    "runtime_flows": "runtime_flows",
    "data_shapes": "data_shapes",
    "persistent_shapes": "persistent_shapes",
    "verticals": "verticals",
    "containers": "containers",
}

COLLECTION_KEYS = {
    "high_level_flows": "high_level_flow",
    "runtime_flows": "runtime_flow",
    "data_shapes": "data_shapes",
    "persistent_shapes": "persistent_shapes",
    "verticals": "verticals",
    "containers": "container",
}


@dataclass
class ForgeSchema:
    root: Path
    system: dict[str, Any]
    runtime: dict[str, Any]
    early_state: list[dict[str, Any]]
    deployment: dict[str, Any]
    high_level_flows: list[dict[str, Any]]
    runtime_flows: list[dict[str, Any]]
    data_shapes: list[dict[str, Any]]
    persistent_shapes: list[dict[str, Any]]
    verticals: list[dict[str, Any]]
    containers: list[dict[str, Any]]

    def index(self, collection: str) -> dict[str, dict[str, Any]]:
        items = getattr(self, collection)
        return {item["id"]: item for item in items if isinstance(item, dict) and item.get("id")}


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return loaded


def dump_yaml(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _unwrap_singleton(path: Path, key: str) -> dict[str, Any]:
    loaded = read_yaml(path)
    value = loaded.get(key, loaded)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain `{key}` as a mapping")
    return value


def _unwrap_collection_item(path: Path, collection: str) -> list[dict[str, Any]]:
    loaded = read_yaml(path)
    value = loaded.get(collection)
    if value is None:
        singular = COLLECTION_KEYS[collection]
        if singular in loaded:
            singular_value = loaded[singular]
            if not isinstance(singular_value, dict):
                raise ValueError(f"{path} must contain `{singular}` as a mapping")
            return [singular_value]
        raise ValueError(f"{path} must contain `{collection}` or `{singular}`")
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain `{collection}` as a list")
    return [item for item in value if isinstance(item, dict)]


def _read_collection(root: Path, collection: str) -> list[dict[str, Any]]:
    directory = root / COLLECTION_DIRS[collection]
    if not directory.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        items.extend(_unwrap_collection_item(path, collection))
    return items


def load_schema(root: Path) -> ForgeSchema:
    system = _unwrap_singleton(root / ROOT_SINGLETONS["system"], "system")
    runtime = _unwrap_singleton(root / ROOT_SINGLETONS["runtime"], "runtime")
    early_state_loaded = read_yaml(root / ROOT_SINGLETONS["early_state"])
    early_state = early_state_loaded.get("early_state", [])
    if not isinstance(early_state, list):
        raise ValueError("early_state.yaml must contain `early_state` as a list")
    deployment = _unwrap_singleton(root / ROOT_SINGLETONS["deployment"], "deployment")
    schema = ForgeSchema(
        root=root,
        system=system,
        runtime=runtime,
        early_state=[item for item in early_state if isinstance(item, dict)],
        deployment=deployment,
        high_level_flows=_read_collection(root, "high_level_flows"),
        runtime_flows=_read_collection(root, "runtime_flows"),
        data_shapes=_read_collection(root, "data_shapes"),
        persistent_shapes=_read_collection(root, "persistent_shapes"),
        verticals=_read_collection(root, "verticals"),
        containers=_read_collection(root, "containers"),
    )
    _validate_schema(schema)
    return schema


def _validate_schema(schema: ForgeSchema) -> None:
    errors: list[str] = []
    _check_system_identity(schema, errors)
    _check_runtime_containers(schema, errors)
    _check_unique_ids(schema, errors)
    _check_cross_references(schema, errors)
    _check_container_components(schema, errors)
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise ValueError(f"Schema validation failed for {schema.root}:\n{joined}")


def _check_system_identity(schema: ForgeSchema, errors: list[str]) -> None:
    if not schema.system.get("id"):
        errors.append("system.yaml must define `system.id`.")


def _check_runtime_containers(schema: ForgeSchema, errors: list[str]) -> None:
    containers = schema.runtime.get("containers", [])
    if not isinstance(containers, list):
        errors.append("runtime.yaml must define `runtime.containers` as a list.")
        return
    seen: set[str] = set()
    for index, container in enumerate(containers, start=1):
        if not isinstance(container, dict):
            errors.append(f"runtime.yaml container #{index} must be a mapping.")
            continue
        container_id = container.get("id")
        if not container_id:
            errors.append(f"runtime.yaml container #{index} is missing `id`.")
            continue
        if container_id in seen:
            errors.append(f"runtime.yaml contains duplicate container id `{container_id}`.")
        seen.add(container_id)


def _check_unique_ids(schema: ForgeSchema, errors: list[str]) -> None:
    _check_collection_ids(schema.early_state, "early_state", errors)
    for collection in (
        "high_level_flows",
        "runtime_flows",
        "data_shapes",
        "persistent_shapes",
        "verticals",
        "containers",
    ):
        _check_collection_ids(getattr(schema, collection), collection, errors)


def _check_collection_ids(items: list[dict[str, Any]], label: str, errors: list[str]) -> None:
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        item_id = item.get("id")
        if not item_id:
            errors.append(f"{label} entry #{index} is missing `id`.")
            continue
        if item_id in seen:
            errors.append(f"{label} contains duplicate id `{item_id}`.")
        seen.add(item_id)


def _check_cross_references(schema: ForgeSchema, errors: list[str]) -> None:
    runtime_container_ids = {
        item.get("id")
        for item in schema.runtime.get("containers", [])
        if isinstance(item, dict) and item.get("id")
    }
    high_level_flow_ids = set(schema.index("high_level_flows"))
    runtime_flow_ids = set(schema.index("runtime_flows"))
    data_shape_ids = set(schema.index("data_shapes"))
    persistent_shape_ids = set(schema.index("persistent_shapes"))

    for vertical in schema.verticals:
        vertical_id = vertical.get("id", "<unknown vertical>")
        _check_reference_list(
            vertical.get("high_level_flows", []),
            high_level_flow_ids,
            errors,
            f"vertical `{vertical_id}` high_level_flows",
        )
        _check_reference_list(
            vertical.get("runtime_containers", []),
            runtime_container_ids,
            errors,
            f"vertical `{vertical_id}` runtime_containers",
        )
        _check_reference_list(
            vertical.get("data_shapes", []),
            data_shape_ids,
            errors,
            f"vertical `{vertical_id}` data_shapes",
        )
        _check_reference_list(
            vertical.get("persistent_shapes", []),
            persistent_shape_ids,
            errors,
            f"vertical `{vertical_id}` persistent_shapes",
        )

    for runtime_flow in schema.runtime_flows:
        flow_id = runtime_flow.get("id", "<unknown runtime flow>")
        high_level_flow = runtime_flow.get("high_level_flow")
        if high_level_flow and high_level_flow not in high_level_flow_ids:
            errors.append(
                f"runtime flow `{flow_id}` references unknown high-level flow `{high_level_flow}`."
            )
        for step in runtime_flow.get("steps", []):
            if not isinstance(step, dict):
                continue
            container_id = step.get("container")
            if container_id and container_id not in runtime_container_ids:
                errors.append(
                    f"runtime flow `{flow_id}` step `{step.get('id', '?')}` references unknown "
                    f"container `{container_id}`."
                )

    for container in schema.containers:
        container_id = container.get("id", "<unknown container>")
        if container_id not in runtime_container_ids:
            errors.append(
                f"container definition `{container_id}` does not match any runtime container in runtime.yaml."
            )
        for component_flow in container.get("component_flows", []):
            if not isinstance(component_flow, dict):
                continue
            runtime_flow = component_flow.get("runtime_flow")
            if runtime_flow and runtime_flow not in runtime_flow_ids:
                errors.append(
                    f"container `{container_id}` component flow `{component_flow.get('id', '?')}` "
                    f"references unknown runtime flow `{runtime_flow}`."
                )

    for persistent_shape in schema.persistent_shapes:
        shape_id = persistent_shape.get("id", "<unknown persistent shape>")
        data_shape = persistent_shape.get("data_shape")
        if data_shape and data_shape not in data_shape_ids:
            errors.append(
                f"persistent shape `{shape_id}` references unknown data shape `{data_shape}`."
            )
        for field_name in ("logical_owner_container", "data_store_container"):
            container_id = persistent_shape.get(field_name)
            if container_id and container_id not in runtime_container_ids:
                errors.append(
                    f"persistent shape `{shape_id}` references unknown container `{container_id}` "
                    f"in `{field_name}`."
                )


def _check_reference_list(
    values: Any,
    known_ids: set[str],
    errors: list[str],
    label: str,
) -> None:
    if not values:
        return
    if not isinstance(values, list):
        errors.append(f"{label} must be a list.")
        return
    for value in values:
        if value not in known_ids:
            errors.append(f"{label} references unknown id `{value}`.")


def _check_container_components(schema: ForgeSchema, errors: list[str]) -> None:
    for container in schema.containers:
        container_id = container.get("id", "<unknown container>")
        component_ids: set[str] = set()
        for index, component in enumerate(container.get("components", []), start=1):
            if not isinstance(component, dict):
                errors.append(f"container `{container_id}` component #{index} must be a mapping.")
                continue
            component_id = component.get("id")
            if not component_id:
                errors.append(f"container `{container_id}` component #{index} is missing `id`.")
                continue
            if component_id in component_ids:
                errors.append(f"container `{container_id}` contains duplicate component `{component_id}`.")
            component_ids.add(component_id)
        for component_flow in container.get("component_flows", []):
            if not isinstance(component_flow, dict):
                continue
            flow_id = component_flow.get("id", "?")
            for step in component_flow.get("steps", []):
                if not isinstance(step, dict):
                    continue
                component_id = step.get("component")
                if component_id and component_id not in component_ids:
                    errors.append(
                        f"container `{container_id}` component flow `{flow_id}` step "
                        f"`{step.get('id', '?')}` references unknown component `{component_id}`."
                    )
