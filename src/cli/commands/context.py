from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from cli.commands.base import add_project_dir_arg
from cli.crawler import ForgeCrawlResult, crawl_project
from cli.yaml_io import dump_yaml


def register_context(subparsers) -> None:
    parser = subparsers.add_parser(
        "context",
        help="Render a scoped Forge V4 context bundle",
        epilog=(
            "Skills-first usage: use forge-schema, forge-build, forge-review, or forge-security "
            "to decide what context you need, then fetch only that scope.\n\n"
            "Examples:\n"
            "  forge context --project-dir . --system --format md\n"
            "  forge context --project-dir . --flow create_note --format json\n"
            "  forge context --project-dir . --container backend_api --format yaml"
        ),
    )
    add_project_dir_arg(parser)
    target = parser.add_mutually_exclusive_group(required=False)
    target.add_argument("--system", action="store_true", help="Return system-level context")
    target.add_argument("--flow", help="Container flow id")
    target.add_argument("--container", help="Container id")
    target.add_argument("--component", help="Component id (requires --container or inferable container)")
    target.add_argument("--entity", help="Entity id")
    target.add_argument("--operation", help="Operation id")
    target.add_argument("--data-shape", dest="data_shape", help="Data shape id")
    parser.add_argument("--mode", choices=["plan", "build", "review"], default="build")
    parser.add_argument("--format", choices=["json", "yaml", "md"], default="json")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    requested_root = Path(args.project_dir).resolve() if args.project_dir else None
    payload = build_v4_context_payload(crawl_project(requested_root or Path.cwd()), args)
    _print_payload(payload, args.format)
    return 0


def _print_payload(payload: dict[str, Any], format_: str) -> None:
    if format_ == "json":
        print(json.dumps(payload, indent=2))
    elif format_ == "yaml":
        print(_yaml_with_header(payload))
    else:
        print(_to_markdown(payload))


def _selected_target(args: Namespace) -> str | None:
    if args.system:
        return "system"
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
    return None


def build_v4_context_payload(result: ForgeCrawlResult, args: Namespace) -> dict[str, Any]:
    target_kind = _selected_target(args)
    model = result.to_dict()
    if target_kind == "system":
        system_id = model["system"].get("id", "system")
        return _v4_payload("system", system_id, args.mode, {"model": model, "knowledge": _knowledge_for_refs(model, [f"system:{system_id}"])})
    if target_kind == "container":
        container = _v4_find(model["containers"], args.container, "container")
        return _v4_payload(
            "container",
            args.container,
            args.mode,
            {"container": container, "knowledge": _knowledge_for_refs(model, [f"container:{args.container}"]), "findings": model["findings"]},
        )
    if target_kind == "flow":
        flow = _v4_find(model["container_flows"], args.flow, "container_flow")
        involved = {
            step.get("container")
            for step in flow.get("steps", [])
            if isinstance(step, dict) and step.get("container")
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
            {
                "container_flow": flow,
                "containers": containers,
                "operations": operations,
                "knowledge": _knowledge_for_refs(model, [f"flow:{args.flow}"] + [f"container:{item}" for item in involved]),
                "findings": model["findings"],
            },
        )
    if target_kind == "entity":
        entity = _v4_find(model["entities"], args.entity, "entity")
        data_shapes = _v4_data_shapes_for_entity(model, args.entity)
        persistence = [item for item in model["persistence"] if item.get("payload", {}).get("entity") == args.entity]
        return _v4_payload(
            "entity",
            args.entity,
            args.mode,
            {
                "entity": entity,
                "data_shapes": data_shapes,
                "persistence": persistence,
                "knowledge": _knowledge_for_refs(model, [f"entity:{args.entity}"]),
                "findings": model["findings"],
            },
        )
    if target_kind == "component":
        component = _v4_find_nested(model["containers"], "components", args.component, "component")
        container = _v4_find(model["containers"], component["container"], "container") if component.get("container") else None
        return _v4_payload(
            "component",
            args.component,
            args.mode,
            {
                "component": component,
                "container": container,
                "knowledge": _knowledge_for_refs(model, [f"component:{args.component}"]),
                "findings": model["findings"],
            },
        )
    if target_kind == "operation":
        operation = _v4_find_nested(model["containers"], "operations", args.operation, "operation")
        container = _v4_find(model["containers"], operation["container"], "container") if operation.get("container") else None
        return _v4_payload(
            "operation",
            args.operation,
            args.mode,
            {
                "operation": operation,
                "container": container,
                "knowledge": _knowledge_for_refs(model, [f"operation:{args.operation}"]),
                "findings": model["findings"],
            },
        )
    if target_kind == "data_shape":
        data_shape = _v4_find_nested(model["containers"], "data_shapes", args.data_shape, "data_shape")
        return _v4_payload(
            "data_shape",
            args.data_shape,
            args.mode,
            {"data_shape": data_shape, "knowledge": _knowledge_for_refs(model, [f"data_shape:{args.data_shape}"]), "findings": model["findings"]},
        )
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


def _knowledge_for_refs(model: dict[str, Any], refs: list[str]) -> list[dict[str, Any]]:
    wanted = set(refs)
    return [
        doc
        for doc in model.get("knowledge", [])
        if isinstance(doc, dict) and wanted.intersection(doc.get("refs", []))
    ]


def _testing_expectations(mode: str) -> dict[str, Any]:
    return {
        "mode": mode,
        "required_levels": ["unit", "integration", "full_system"],
        "environment": "current_target_environment",
    }


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
