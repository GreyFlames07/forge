from __future__ import annotations

from argparse import ArgumentParser, Namespace
from difflib import get_close_matches
from pathlib import Path

from cli.commands.base import add_forge_dir_arg
from cli.common import find_forge_root
from cli.schema import dump_yaml, load_schema
from cli.workbench import read_yaml


def register_context(subparsers) -> None:
    parser = subparsers.add_parser("context", help="Render a schema-aware context bundle for an id")
    add_forge_dir_arg(parser)
    parser.add_argument("target", help="Schema object id")
    parser.add_argument("--format", choices=["yaml", "markdown"], default="yaml")
    parser.set_defaults(func=run)


def _iter_id_refs(value, valid_ids: set[str]) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, str):
        if value in valid_ids:
            refs.add(value)
        return refs
    if isinstance(value, dict):
        for inner in value.values():
            refs.update(_iter_id_refs(inner, valid_ids))
        return refs
    if isinstance(value, list):
        for inner in value:
            refs.update(_iter_id_refs(inner, valid_ids))
    return refs


def _object_group(schema, target_id: str) -> str | None:
    for group_name, items in schema.collections.items():
        if any(item.get("id") == target_id for item in items):
            return group_name
    for group_name, items in schema.verification.items():
        if any(item.get("id") == target_id for item in items):
            return f"verification.{group_name}"
    if schema.system.get("id") == target_id:
        return "system"
    if schema.bootstrap.get("id") == target_id:
        return "bootstrap"
    if schema.build_policy.get("id") == target_id:
        return "build_policy"
    return None


def _is_bootstrap_related(schema, target_id: str) -> bool:
    return target_id in _iter_id_refs(schema.bootstrap, set(schema.index_by_id()))


def _implementation_hints(schema, target: dict, group: str | None) -> list[str]:
    root = schema.root.parent
    hints: list[str] = []
    target_id = target["id"]

    def add_hint(path: Path) -> None:
        rel = path.relative_to(root)
        value = rel.as_posix()
        if value not in hints:
            hints.append(value)

    if group == "units":
        entrypoint = target.get("entrypoint")
        if entrypoint:
            add_hint(root / entrypoint)
    elif group == "operations":
        unit = next((item for item in schema.collections["units"] if item.get("id") == target.get("unit")), None)
        entrypoint = unit.get("entrypoint") if unit else None
        if entrypoint:
            base = (root / entrypoint).parent
            add_hint(base / "operations" / f"{target_id}.py")
            add_hint(base / "operations" / f"{target_id}.ts")
            add_hint(base / f"{target_id}.py")
            add_hint(base / f"{target_id}.ts")
    elif group == "surfaces":
        unit = next((item for item in schema.collections["units"] if item.get("id") == target.get("unit")), None)
        entrypoint = unit.get("entrypoint") if unit else None
        if entrypoint:
            base = (root / entrypoint).parent
            add_hint(base / "surfaces" / f"{target_id}.py")
            add_hint(base / "surfaces" / f"{target_id}.ts")
            add_hint(base / "routes" / f"{target_id}.py")
            add_hint(base / "routes" / f"{target_id}.ts")
    elif group == "types":
        vertical = target.get("vertical")
        if vertical:
            add_hint(root / "packages" / "types" / f"{target_id}.ts")
            add_hint(root / "packages" / "types" / f"{target_id}.py")
            add_hint(root / "packages" / "contracts" / f"{target_id}.ts")
            add_hint(root / "packages" / "contracts" / f"{target_id}.py")
    return hints


def _verification_refs(schema, target_id: str, group: str | None) -> dict:
    refs = {"startup": [], "surfaces": [], "flows": [], "all": []}
    if group == "units":
        refs["startup"] = [item for item in schema.verification["startup"] if item.get("unit") == target_id]
    if group == "surfaces":
        refs["surfaces"] = [item for item in schema.verification["surfaces"] if item.get("surface") == target_id]
    if group == "flows":
        refs["flows"] = [item for item in schema.verification["flows"] if item.get("flow") == target_id]
    if group == "operations":
        refs["surfaces"] = [
            item for item in schema.verification["surfaces"]
            if any(surface.get("id") == item.get("surface") for surface in schema.collections["surfaces"] if surface.get("operation") == target_id)
        ]
        refs["flows"] = [
            item for item in schema.verification["flows"]
            if any(step.get("ref") == target_id for flow in schema.collections["flows"] if flow.get("id") == item.get("flow") for step in flow.get("path", []))
        ]
    refs["all"] = refs["startup"] + refs["surfaces"] + refs["flows"]
    return refs


def _related(schema, target: dict) -> dict:
    idx = schema.index_by_id()
    target_id = target["id"]
    valid_ids = set(idx)
    related = {
        "references": sorted(_iter_id_refs(target, valid_ids) - {target_id}),
        "referenced_by": [],
    }
    for item_id, item in idx.items():
        if item_id == target_id:
            continue
        if target_id in _iter_id_refs(item, valid_ids):
            related["referenced_by"].append(item_id)
    related["referenced_by"] = sorted(set(related["referenced_by"]))
    return related


def _context_bundle(schema, target: dict) -> dict:
    idx = schema.index_by_id()
    group = _object_group(schema, target["id"])
    bundle = {"target": target, "related": _related(schema, target)}
    plan = read_yaml(schema.root / "workbench" / "plan.yaml")
    status = read_yaml(schema.root / "workbench" / "status.yaml")
    validation_report = (schema.root / "workbench" / "validation.md")

    touched_slices = []
    for slice_item in plan.get("slices", []):
        touches = slice_item.get("touches", {})
        refs = set()
        for values in touches.values():
            if isinstance(values, list):
                refs.update(values)
        if target.get("id") in refs:
            touched_slices.append(slice_item)

    bundle["workbench"] = {
        "slices": touched_slices,
        "status": status,
        "validation_report_exists": validation_report.exists(),
        "validation_summary": status.get("validation_summary", {}),
    }
    bundle["implementation_hints"] = _implementation_hints(schema, target, group)
    bundle["verification_refs"] = _verification_refs(schema, target["id"], group)

    if group == "operations":
        bundle["owning_vertical"] = idx.get(target.get("vertical"))
        bundle["owning_unit"] = idx.get(target.get("unit"))
        bundle["input_types"] = [idx[ref] for ref in target.get("inputs", []) if ref in idx]
        bundle["output_types"] = [idx[ref] for ref in target.get("outputs", []) if ref in idx]
        bundle["referenced_types"] = [idx[ref] for ref in target.get("referenced_types", []) if ref in idx]
        bundle["error_types"] = [idx[ref] for ref in target.get("errors", []) if ref in idx]
        bundle["read_stores"] = [idx[ref] for ref in target.get("reads", {}).get("stores", []) if ref in idx]
        bundle["write_stores"] = [idx[ref] for ref in target.get("writes", {}).get("stores", []) if ref in idx]
        bundle["surfaces"] = [item for item in schema.collections["surfaces"] if item.get("operation") == target["id"]]
        bundle["flows"] = [
            item
            for item in schema.collections["flows"]
            if any(step.get("ref") == target["id"] for step in item.get("path", []))
        ]
        bundle["triggered_transitions"] = [
            type_item
            for type_item in schema.collections["types"]
            if any(transition.get("via") == target["id"] for transition in type_item.get("lifecycle", {}).get("transitions", []))
        ]
        bundle["bootstrap_relevance"] = _is_bootstrap_related(schema, target["id"])
        bundle["contract_refs"] = {
            "inputs": target.get("inputs", []),
            "outputs": target.get("outputs", []),
            "referenced_types": target.get("referenced_types", []),
            "errors": target.get("errors", []),
            "reads": target.get("reads", {}).get("types", []),
            "writes": target.get("writes", {}).get("types", []),
            "emits": target.get("emits", []),
            "consumes": target.get("consumes", []),
        }
        bundle["runtime_refs"] = {
            "unit": target.get("unit"),
            "read_stores": target.get("reads", {}).get("stores", []),
            "write_stores": target.get("writes", {}).get("stores", []),
            "surfaces": [item["id"] for item in bundle["surfaces"]],
            "flows": [item["id"] for item in bundle["flows"]],
        }
    elif group == "flows":
        bundle["owning_vertical"] = idx.get(target.get("vertical"))
        bundle["steps"] = [idx[step["ref"]] for step in target.get("path", []) if step.get("ref") in idx]
        bundle["bootstrap_relevance"] = _is_bootstrap_related(schema, target["id"])
    elif group == "units":
        bundle["verticals"] = [idx[ref] for ref in target.get("serves_verticals", []) if ref in idx]
        bundle["surfaces"] = [item for item in schema.collections["surfaces"] if item.get("unit") == target["id"]]
        bundle["operations"] = [item for item in schema.collections["operations"] if item.get("unit") == target["id"]]
        bundle["startup_checks"] = bundle["verification_refs"]["startup"]
        bundle["bootstrap_relevance"] = target["id"] in schema.bootstrap.get("required_units", [])
    elif group == "verticals":
        bundle["units"] = [item for item in schema.collections["units"] if target["id"] in item.get("serves_verticals", [])]
        bundle["operations"] = [item for item in schema.collections["operations"] if item.get("vertical") == target["id"]]
        bundle["surfaces"] = [item for item in schema.collections["surfaces"] if item.get("vertical") == target["id"]]
        bundle["flows"] = [item for item in schema.collections["flows"] if item.get("vertical") == target["id"]]
        bundle["bootstrap_overlap"] = any(
            item.get("id") in schema.bootstrap.get("required_units", [])
            for item in bundle["units"]
        )
    return bundle


def _to_markdown(payload: dict) -> str:
    target = payload["target"]
    related = payload["related"]
    lines = [f"# Context: {target['id']}", "", f"- kind: `{target.get('kind', 'unknown')}`"]
    if target.get("name"):
        lines.append(f"- name: `{target['name']}`")
    if target.get("description"):
        lines.append(f"- description: {target['description']}")
    if related["references"]:
        lines.append(f"- references: {', '.join(f'`{ref}`' for ref in related['references'])}")
    if related["referenced_by"]:
        lines.append(f"- referenced by: {', '.join(f'`{ref}`' for ref in related['referenced_by'])}")
    if payload.get("implementation_hints"):
        lines.append(f"- likely implementation paths: {', '.join(f'`{path}`' for path in payload['implementation_hints'])}")
    if payload.get("verification_refs", {}).get("all"):
        lines.append(
            f"- verification refs: {', '.join(f'`{item['id']}`' for item in payload['verification_refs']['all'])}"
        )
    slices = payload.get("workbench", {}).get("slices", [])
    if slices:
        lines.append(f"- workbench slices: {', '.join(f'`{item['id']}`' for item in slices)}")
    lines.append("")
    lines.append("```yaml")
    lines.append(dump_yaml(target).rstrip())
    lines.append("```")
    return "\n".join(lines)


def _suggest_ids(schema, raw_target: str, limit: int = 5) -> list[str]:
    idx = schema.index_by_id()
    ids = sorted(idx)
    suggestions = get_close_matches(raw_target, ids, n=limit, cutoff=0.45)
    if suggestions:
        return suggestions
    lowered = raw_target.lower()
    contains = [item_id for item_id in ids if lowered in item_id.lower()]
    return contains[:limit]


def run(args: Namespace) -> int:
    forge_root = Path(args.forge_dir).resolve() if args.forge_dir else find_forge_root()
    schema = load_schema(forge_root)
    target = schema.index_by_id().get(args.target)
    if not target:
        print(f"Unknown id: {args.target}")
        suggestions = _suggest_ids(schema, args.target)
        if suggestions:
            print("Did you mean:")
            for suggestion in suggestions:
                print(f"- {suggestion}")
        return 1
    payload = _context_bundle(schema, target)
    if args.format == "markdown":
        print(_to_markdown(payload))
    else:
        print(f"# Context: {target['id']}")
        print(f"# Kind: {target.get('kind', 'unknown')}")
        print(dump_yaml(payload))
    return 0
