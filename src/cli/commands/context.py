from __future__ import annotations

import json
import re
from argparse import Namespace
from pathlib import Path
from typing import Any

from cli.commands.base import add_project_dir_arg
from cli.common import find_project_root
from cli.crawler import ForgeCrawlResult, crawl_project
from cli.schema import ForgeSchema, dump_yaml, load_schema

REF_PATTERN = re.compile(r"ref\[([a-zA-Z0-9_]+)\]")


def register_context(subparsers) -> None:
    parser = subparsers.add_parser(
        "context",
        help="Render a scoped Forge V3 context bundle",
        epilog=(
            "Skills-first usage: use forge-schema, forge-build, forge-review, or forge-security "
            "to decide what context you need, then fetch only that scope.\n\n"
            "Examples:\n"
            "  forge context --project-dir . --system --format md\n"
            "  forge context --project-dir . --vertical place_order --format json\n"
            "  forge context --project-dir . --container ordering_api --format yaml"
        ),
    )
    add_project_dir_arg(parser)
    target = parser.add_mutually_exclusive_group(required=False)
    target.add_argument("--system", action="store_true", help="Return system-level context")
    target.add_argument("--vertical", help="Vertical id")
    target.add_argument("--flow", help="Runtime flow id")
    target.add_argument("--container", help="Container id")
    target.add_argument("--component", help="Component id (requires --container or inferable container)")
    target.add_argument("--entity", help="Entity id")
    target.add_argument("--operation", help="Operation id")
    target.add_argument("--data-shape", dest="data_shape", help="Data shape id")
    target.add_argument("--persistent-shape", dest="persistent_shape", help="Persistent shape id")
    parser.add_argument("--mode", choices=["plan", "build", "review"], default="build")
    parser.add_argument("--format", choices=["json", "yaml", "md"], default="json")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    requested_root = Path(args.project_dir).resolve() if args.project_dir else None
    v4_payload = _try_v4_context(requested_root, args)
    if v4_payload is not None:
        _print_payload(v4_payload, args.format)
        return 0
    root = find_project_root(requested_root)
    schema = load_schema(root)
    payload = build_context_payload(schema, args)
    _print_payload(payload, args.format)
    return 0


def _print_payload(payload: dict[str, Any], format_: str) -> None:
    if format_ == "json":
        print(json.dumps(payload, indent=2))
    elif format_ == "yaml":
        print(_yaml_with_header(payload))
    else:
        print(_to_markdown(payload))


def _try_v4_context(root: Path | None, args: Namespace) -> dict[str, Any] | None:
    try:
        result = crawl_project(root or Path.cwd())
    except FileNotFoundError:
        return None
    return build_v4_context_payload(result, args)


def build_context_payload(schema: ForgeSchema, args: Namespace) -> dict[str, Any]:
    target_kind = _selected_target(args)
    if target_kind == "system":
        return _system_context(schema, args.mode)
    if target_kind == "vertical":
        return _vertical_context(schema, args.vertical, args.mode)
    if target_kind == "flow":
        return _flow_context(schema, args.flow, args.mode)
    if target_kind == "container":
        return _container_context(schema, args.container, args.mode, component_id=args.component)
    if target_kind == "component":
        container_id = _find_container_for_component(schema, args.component)
        if not container_id:
            raise ValueError(f"Could not infer container for component `{args.component}`. Pass --container.")
        return _container_context(schema, container_id, args.mode, component_id=args.component)
    if target_kind == "data_shape":
        return _data_shape_context(schema, args.data_shape, args.mode)
    if target_kind == "persistent_shape":
        return _persistent_shape_context(schema, args.persistent_shape, args.mode)
    raise ValueError(
        "No context target selected. Choose one of --system, --vertical, --flow, "
        "--container, --component, --data-shape, or --persistent-shape. "
        "Start from the active skill, then request only the narrowest scope you need."
    )


def _selected_target(args: Namespace) -> str | None:
    if args.system:
        return "system"
    if args.vertical:
        return "vertical"
    if args.flow:
        return "flow"
    if args.container:
        return "container"
    if args.component:
        return "component"
    if getattr(args, "entity", None):
        return "entity"
    if getattr(args, "operation", None):
        return "operation"
    if args.data_shape:
        return "data_shape"
    if args.persistent_shape:
        return "persistent_shape"
    return None


def build_v4_context_payload(result: ForgeCrawlResult, args: Namespace) -> dict[str, Any]:
    target_kind = _selected_target(args)
    model = result.to_dict()
    if target_kind == "system":
        return _v4_payload("system", model["system"].get("id", "system"), args.mode, {"model": model})
    if target_kind == "container":
        container = _v4_find(model["containers"], args.container, "container")
        return _v4_payload("container", args.container, args.mode, {"container": container, "findings": model["findings"]})
    if target_kind == "flow":
        flow = _v4_find(model["container_flows"], args.flow, "container_flow")
        involved = {
            step.get("from")
            for step in flow.get("steps", [])
            if isinstance(step, dict) and step.get("from")
        } | {
            step.get("to")
            for step in flow.get("steps", [])
            if isinstance(step, dict) and step.get("to")
        }
        containers = [container for container in model["containers"] if container.get("id") in involved]
        operations = [
            operation
            for container in containers
            for operation in container.get("operations", [])
            if _v4_operation_in_flow(operation, args.flow)
        ]
        return _v4_payload(
            "container_flow",
            args.flow,
            args.mode,
            {"container_flow": flow, "containers": containers, "operations": operations, "findings": model["findings"]},
        )
    if target_kind == "entity":
        entity = _v4_find(model["entities"], args.entity, "entity")
        data_shapes = _v4_data_shapes_for_entity(model, args.entity)
        persistence = [item for item in model["persistence"] if item.get("payload", {}).get("entity") == args.entity]
        return _v4_payload(
            "entity",
            args.entity,
            args.mode,
            {"entity": entity, "data_shapes": data_shapes, "persistence": persistence, "findings": model["findings"]},
        )
    if target_kind == "component":
        component = _v4_find_nested(model["containers"], "components", args.component, "component")
        container = _v4_find(model["containers"], component["container"], "container") if component.get("container") else None
        return _v4_payload(
            "component",
            args.component,
            args.mode,
            {"component": component, "container": container, "findings": model["findings"]},
        )
    if target_kind == "operation":
        operation = _v4_find_nested(model["containers"], "operations", args.operation, "operation")
        container = _v4_find(model["containers"], operation["container"], "container") if operation.get("container") else None
        return _v4_payload("operation", args.operation, args.mode, {"operation": operation, "container": container, "findings": model["findings"]})
    if target_kind == "data_shape":
        data_shape = _v4_find_nested(model["containers"], "data_shapes", args.data_shape, "data_shape")
        return _v4_payload("data_shape", args.data_shape, args.mode, {"data_shape": data_shape, "findings": model["findings"]})
    raise ValueError(
        "No context target selected. Choose one of --system, --flow, --container, "
        "--entity, --component, --operation, or --data-shape."
    )


def _v4_payload(type_: str, id_: str, mode: str, artifacts: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": _target(type_, id_, mode),
        "summary": _summary_from_item(artifacts.get(type_, {}) if isinstance(artifacts.get(type_), dict) else {}),
        "artifacts": artifacts,
        "testing": _testing_expectations(mode),
    }


def _v4_find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item.get("id") == item_id:
            return item
    raise FileNotFoundError(f"Unknown {label}: {item_id}")


def _v4_find_nested(containers: list[dict[str, Any]], collection: str, item_id: str, label: str) -> dict[str, Any]:
    for container in containers:
        for item in container.get(collection, []):
            if item.get("id") == item_id:
                return item
    raise FileNotFoundError(f"Unknown {label}: {item_id}")


def _v4_operation_in_flow(operation: dict[str, Any], flow_id: str) -> bool:
    payload = operation.get("payload", {})
    if payload.get("container_flow") == flow_id:
        return True
    return any(item.get("container_flow") == flow_id for item in payload.get("participates_in", []) if isinstance(item, dict))


def _v4_data_shapes_for_entity(model: dict[str, Any], entity_id: str) -> list[dict[str, Any]]:
    shapes: list[dict[str, Any]] = []
    for container in model["containers"]:
        for shape in container.get("data_shapes", []):
            if shape.get("payload", {}).get("entity") == entity_id:
                shapes.append(shape)
    return shapes


def _yaml_with_header(payload: dict[str, Any]) -> str:
    header = f"# Context: {payload['target']['id']}\n# Type: {payload['target']['type']}\n"
    return header + dump_yaml(payload)


def _to_markdown(payload: dict[str, Any]) -> str:
    target = payload["target"]
    lines = [
        f"# Context: {target['id']}",
        "",
        f"- type: `{target['type']}`",
        f"- mode: `{payload['target']['mode']}`",
    ]
    summary = payload.get("summary", {})
    if summary.get("description"):
        lines.append(f"- description: {summary['description']}")
    if summary.get("user_value"):
        lines.append(f"- user value: {summary['user_value']}")
    if payload.get("implementation_scope", {}).get("involved_containers"):
        lines.append(
            "- involved containers: "
            + ", ".join(f"`{item}`" for item in payload["implementation_scope"]["involved_containers"])
        )
    lines.extend(["", "```yaml", dump_yaml(payload).rstrip(), "```"])
    return "\n".join(lines)


def _target(type_: str, id_: str, mode: str) -> dict[str, str]:
    return {"type": type_, "id": id_, "mode": mode}


def _summary_from_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": item.get("description"),
        "user_value": item.get("user_value"),
    }


def _container_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in schema.runtime.get("containers", []) if item.get("id")}


def _high_level_flow_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("high_level_flows")


def _runtime_flow_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("runtime_flows")


def _data_shape_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("data_shapes")


def _persistent_shape_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("persistent_shapes")


def _vertical_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("verticals")


def _container_artifact_index(schema: ForgeSchema) -> dict[str, dict[str, Any]]:
    return schema.index("containers")


def _extract_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        refs.update(REF_PATTERN.findall(value))
        return refs
    if isinstance(value, list):
        for item in value:
            refs.update(_extract_refs(item))
        return refs
    if isinstance(value, dict):
        for item in value.values():
            refs.update(_extract_refs(item))
    return refs


def _deployment_nodes_for_containers(schema: ForgeSchema, container_ids: set[str]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for environment in schema.deployment.get("environments", []):
        if not isinstance(environment, dict):
            continue
        for node in environment.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_containers = set(node.get("containers", []))
            if node_containers & container_ids:
                nodes.append({"environment": environment.get("id"), **node})
    return nodes


def _security_constraints(system: dict[str, Any], containers: list[dict[str, Any]], persistent_shapes: list[dict[str, Any]]) -> list[str]:
    constraints: list[str] = []
    if system.get("security"):
        constraints.append(system["security"])
    constraints.extend(item["security"] for item in containers if item.get("security"))
    constraints.extend(item["security"] for item in persistent_shapes if item.get("security"))
    return constraints


def _testing_expectations(mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "required_levels": ["unit", "integration", "full_system"],
        "environment": "current_target_environment",
    }


def _vertical_context(schema: ForgeSchema, vertical_id: str, mode: str) -> dict[str, Any]:
    vertical = _vertical_index(schema).get(vertical_id)
    if not vertical:
        raise FileNotFoundError(f"Unknown vertical: {vertical_id}")
    high_level_flows = [
        _high_level_flow_index(schema)[flow_id]
        for flow_id in vertical.get("high_level_flows", [])
        if flow_id in _high_level_flow_index(schema)
    ]
    runtime_flows = [
        flow
        for flow in schema.runtime_flows
        if flow.get("high_level_flow") in vertical.get("high_level_flows", [])
    ]
    runtime_container_index = _container_index(schema)
    runtime_containers = [
        runtime_container_index[item_id]
        for item_id in vertical.get("runtime_containers", [])
        if item_id in runtime_container_index
    ]
    data_shape_index = _data_shape_index(schema)
    data_shapes = [
        data_shape_index[item_id]
        for item_id in vertical.get("data_shapes", [])
        if item_id in data_shape_index
    ]
    persistent_shape_index = _persistent_shape_index(schema)
    persistent_shapes = [
        persistent_shape_index[item_id]
        for item_id in vertical.get("persistent_shapes", [])
        if item_id in persistent_shape_index
    ]
    container_artifact_index = _container_artifact_index(schema)
    containers = [
        container_artifact_index[item_id]
        for item_id in vertical.get("runtime_containers", [])
        if item_id in container_artifact_index
    ]
    container_ids = {item["id"] for item in runtime_containers}
    return {
        "target": _target("vertical", vertical_id, mode),
        "summary": _summary_from_item(vertical),
        "artifacts": {
            "vertical": vertical,
            "high_level_flows": high_level_flows,
            "runtime_flows": runtime_flows,
            "runtime": schema.runtime,
            "containers": containers,
            "data_shapes": data_shapes,
            "persistent_shapes": persistent_shapes,
            "deployment_nodes": _deployment_nodes_for_containers(schema, container_ids),
        },
        "implementation_scope": {
            "involved_containers": sorted(container_ids),
            "involved_components": sorted(
                {
                    component["id"]
                    for container in containers
                    for component in container.get("components", [])
                    if isinstance(component, dict) and component.get("id")
                }
            ),
            "relevant_shapes": [item["id"] for item in data_shapes],
            "relevant_persistent_shapes": [item["id"] for item in persistent_shapes],
        },
        "constraints": {
            "security": _security_constraints(schema.system, runtime_containers, persistent_shapes),
            "build_notes": vertical.get("build_notes"),
            "deployment_notes": vertical.get("deployment_notes"),
            "anti_bloat_rules": [
                "Default to inline one-off payloads.",
                "Promote only reused, persisted, or important shapes.",
                "Do not broaden scope beyond the current vertical slice.",
            ],
        },
        "testing": _testing_expectations(mode),
    }


def _flow_context(schema: ForgeSchema, flow_id: str, mode: str) -> dict[str, Any]:
    flow = _runtime_flow_index(schema).get(flow_id)
    if not flow:
        raise FileNotFoundError(f"Unknown runtime flow: {flow_id}")
    high_level_flow = _high_level_flow_index(schema).get(flow.get("high_level_flow"))
    container_ids = {
        step["container"]
        for step in flow.get("steps", [])
        if isinstance(step, dict) and step.get("container")
    }
    runtime_containers = [
        _container_index(schema)[container_id]
        for container_id in sorted(container_ids)
        if container_id in _container_index(schema)
    ]
    container_artifacts = [
        _container_artifact_index(schema)[container_id]
        for container_id in sorted(container_ids)
        if container_id in _container_artifact_index(schema)
    ]
    refs = _extract_refs(flow)
    data_shape_index = _data_shape_index(schema)
    data_shapes = [data_shape_index[ref] for ref in sorted(refs) if ref in data_shape_index]
    persistent_shapes = [
        item
        for item in schema.persistent_shapes
        if item.get("data_shape") in refs or item.get("logical_owner_container") in container_ids or item.get("data_store_container") in container_ids
    ]
    related_verticals = [
        vertical
        for vertical in schema.verticals
        if flow.get("high_level_flow") in vertical.get("high_level_flows", [])
    ]
    return {
        "target": _target("runtime_flow", flow_id, mode),
        "summary": _summary_from_item(flow),
        "artifacts": {
            "runtime_flow": flow,
            "high_level_flow": high_level_flow,
            "runtime_containers": runtime_containers,
            "containers": container_artifacts,
            "data_shapes": data_shapes,
            "persistent_shapes": persistent_shapes,
            "related_verticals": related_verticals,
            "deployment_nodes": _deployment_nodes_for_containers(schema, container_ids),
        },
        "implementation_scope": {
            "involved_containers": sorted(container_ids),
            "relevant_shapes": [item["id"] for item in data_shapes],
            "relevant_persistent_shapes": [item["id"] for item in persistent_shapes],
        },
        "constraints": {
            "security": _security_constraints(schema.system, runtime_containers, persistent_shapes),
            "anti_bloat_rules": [
                "Keep runtime steps container-level only.",
                "Keep one-off payloads inline unless promoted.",
            ],
        },
        "testing": _testing_expectations(mode),
    }


def _container_context(schema: ForgeSchema, container_id: str, mode: str, component_id: str | None = None) -> dict[str, Any]:
    runtime_container = _container_index(schema).get(container_id)
    if not runtime_container:
        raise FileNotFoundError(f"Unknown runtime container: {container_id}")
    container_artifact = _container_artifact_index(schema).get(container_id)
    runtime_flows = []
    refs: set[str] = set()
    for flow in schema.runtime_flows:
        if any(step.get("container") == container_id for step in flow.get("steps", []) if isinstance(step, dict)):
            runtime_flows.append(flow)
            refs.update(_extract_refs(flow))
    verticals = [
        vertical for vertical in schema.verticals if container_id in vertical.get("runtime_containers", [])
    ]
    data_shape_index = _data_shape_index(schema)
    data_shapes = [data_shape_index[ref] for ref in sorted(refs) if ref in data_shape_index]
    persistent_shapes = [
        item
        for item in schema.persistent_shapes
        if item.get("logical_owner_container") == container_id or item.get("data_store_container") == container_id
    ]
    component = None
    component_flows: list[dict[str, Any]] = []
    if container_artifact:
        if component_id:
            for candidate in container_artifact.get("components", []):
                if candidate.get("id") == component_id:
                    component = candidate
                    break
            if not component:
                raise FileNotFoundError(f"Unknown component `{component_id}` in container `{container_id}`")
        component_flows = _filter_component_flows(container_artifact, component_id)
    return {
        "target": _target("component" if component_id else "container", component_id or container_id, mode),
        "summary": {
            "description": component.get("description") if component else runtime_container.get("description"),
        },
        "artifacts": {
            "runtime_container": runtime_container,
            "container": container_artifact,
            "component": component,
            "component_flows": component_flows,
            "runtime_flows": runtime_flows,
            "verticals": verticals,
            "data_shapes": data_shapes,
            "persistent_shapes": persistent_shapes,
            "deployment_nodes": _deployment_nodes_for_containers(schema, {container_id}),
        },
        "implementation_scope": {
            "involved_containers": [container_id],
            "involved_components": [component_id] if component_id else [
                item["id"] for item in container_artifact.get("components", [])
            ] if container_artifact else [],
            "relevant_shapes": [item["id"] for item in data_shapes],
            "relevant_persistent_shapes": [item["id"] for item in persistent_shapes],
        },
        "constraints": {
            "security": _security_constraints(schema.system, [runtime_container], persistent_shapes),
            "anti_bloat_rules": [
                "Do not model classes or files as components.",
                "Keep component flows as inter-component handoffs only.",
            ],
        },
        "testing": _testing_expectations(mode),
    }


def _filter_component_flows(container_artifact: dict[str, Any], component_id: str | None) -> list[dict[str, Any]]:
    if not component_id:
        return container_artifact.get("component_flows", [])
    flows: list[dict[str, Any]] = []
    for flow in container_artifact.get("component_flows", []):
        steps = [
            step
            for step in flow.get("steps", [])
            if isinstance(step, dict) and step.get("component") == component_id
        ]
        if steps:
            narrowed = dict(flow)
            narrowed["steps"] = steps
            flows.append(narrowed)
    return flows


def _find_container_for_component(schema: ForgeSchema, component_id: str) -> str | None:
    for container in schema.containers:
        for component in container.get("components", []):
            if isinstance(component, dict) and component.get("id") == component_id:
                return container.get("id")
    return None


def _system_context(schema: ForgeSchema, mode: str) -> dict[str, Any]:
    runtime_containers = list(_container_index(schema).values())
    return {
        "target": _target("system", schema.system["id"], mode),
        "summary": {
            "description": schema.system.get("description"),
        },
        "artifacts": {
            "system": schema.system,
            "runtime": schema.runtime,
            "early_state": schema.early_state,
            "deployment": schema.deployment,
            "verticals": schema.verticals,
        },
        "implementation_scope": {
            "involved_containers": [item["id"] for item in runtime_containers],
        },
        "constraints": {
            "security": _security_constraints(schema.system, runtime_containers, schema.persistent_shapes),
        },
        "testing": _testing_expectations(mode),
    }


def _data_shape_context(schema: ForgeSchema, data_shape_id: str, mode: str) -> dict[str, Any]:
    data_shape = _data_shape_index(schema).get(data_shape_id)
    if not data_shape:
        raise FileNotFoundError(f"Unknown data shape: {data_shape_id}")
    runtime_flows = [flow for flow in schema.runtime_flows if data_shape_id in _extract_refs(flow)]
    containers = [
        _container_artifact_index(schema)[container_id]
        for flow in runtime_flows
        for container_id in {
            step.get("container")
            for step in flow.get("steps", [])
            if isinstance(step, dict) and step.get("container") in _container_artifact_index(schema)
        }
    ]
    persistent_shapes = [item for item in schema.persistent_shapes if item.get("data_shape") == data_shape_id]
    return {
        "target": _target("data_shape", data_shape_id, mode),
        "summary": _summary_from_item(data_shape),
        "artifacts": {
            "data_shape": data_shape,
            "runtime_flows": runtime_flows,
            "containers": containers,
            "persistent_shapes": persistent_shapes,
        },
        "implementation_scope": {
            "relevant_shapes": [data_shape_id],
            "relevant_persistent_shapes": [item["id"] for item in persistent_shapes],
        },
        "constraints": {
            "security": [item["security"] for item in persistent_shapes if item.get("security")],
        },
        "testing": _testing_expectations(mode),
    }


def _persistent_shape_context(schema: ForgeSchema, persistent_shape_id: str, mode: str) -> dict[str, Any]:
    persistent_shape = _persistent_shape_index(schema).get(persistent_shape_id)
    if not persistent_shape:
        raise FileNotFoundError(f"Unknown persistent shape: {persistent_shape_id}")
    data_shape = _data_shape_index(schema).get(persistent_shape.get("data_shape"))
    container_ids = {
        persistent_shape.get("logical_owner_container"),
        persistent_shape.get("data_store_container"),
    } - {None}
    runtime_containers = [
        _container_index(schema)[container_id]
        for container_id in sorted(container_ids)
        if container_id in _container_index(schema)
    ]
    deployment_nodes = _deployment_nodes_for_containers(schema, container_ids)
    return {
        "target": _target("persistent_shape", persistent_shape_id, mode),
        "summary": _summary_from_item(persistent_shape),
        "artifacts": {
            "persistent_shape": persistent_shape,
            "data_shape": data_shape,
            "runtime_containers": runtime_containers,
            "deployment_nodes": deployment_nodes,
        },
        "implementation_scope": {
            "involved_containers": sorted(container_ids),
            "relevant_shapes": [data_shape["id"]] if data_shape else [],
            "relevant_persistent_shapes": [persistent_shape_id],
        },
        "constraints": {
            "security": _security_constraints(schema.system, runtime_containers, [persistent_shape]),
        },
        "testing": _testing_expectations(mode),
    }
