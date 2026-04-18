"""`forge inspect <id>` — lightweight metadata probe for any id."""

from __future__ import annotations

import argparse
import sys
from collections import OrderedDict
from typing import Any

import yaml

from cli import common

NAME = "inspect"
HELP = "Show lightweight metadata for an id (no full bundle expansion)."
DESCRIPTION = (
    "Prints kind, file path, description, owner, and direct "
    "dependencies for <id>. Useful for quick 'does this exist and "
    "what is it?' probes before calling `forge context`."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument("id", help="Any id present in the spec directory.")
    common.add_spec_dir_arg(p)
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    entry = idx.get(args.id)
    if entry is None:
        print(f"error: unknown id: {args.id}", file=sys.stderr)
        common.suggest_similar(idx, args.id)
        return 1

    info: OrderedDict[str, Any] = OrderedDict()
    info["id"] = entry.id
    info["kind"] = entry.kind
    if entry.file:
        info["file"] = (
            str(entry.file.relative_to(idx.spec_dir))
            if entry.file.is_relative_to(idx.spec_dir)
            else str(entry.file)
        )
    desc = common.full_description(entry.data)
    if desc:
        info["description"] = desc

    data = entry.data if isinstance(entry.data, dict) else {}
    _populate_kind_extras(info, entry.kind, data)

    if entry.kind in common.BUNDLEABLE_KINDS:
        info["bundleable"] = True
        info["bundle_command"] = f"forge context {entry.id}"
    else:
        info["bundleable"] = False

    sys.stdout.write(yaml.dump(
        dict(info), sort_keys=False, allow_unicode=True,
        default_flow_style=False, width=100,
    ))
    return 0


def _populate_kind_extras(info: OrderedDict[str, Any], kind: str, data: dict[str, Any]) -> None:
    """Add per-kind useful metadata to the inspect output."""
    if kind == "atom":
        spec = data.get("spec") or {}
        info["atom_kind"] = data.get("kind")
        info["owner_module"] = data.get("owner_module")
        info["side_effects"] = spec.get("side_effects") or []
        info["output_errors"] = (spec.get("output") or {}).get("errors") or []
    elif kind == "module":
        info["owned_atoms"] = data.get("owned_atoms") or []
        info["owned_artifacts"] = data.get("owned_artifacts") or []
        info["dependency_whitelist"] = (data.get("dependency_whitelist") or {}).get("modules") or []
        info["policies"] = data.get("policies") or []
    elif kind == "flow":
        info["transaction_boundary"] = data.get("transaction_boundary")
        info["trigger"] = data.get("trigger")
        info["steps"] = [s.get("step") for s in data.get("sequence") or []]
    elif kind == "journey":
        info["surface"] = data.get("surface")
        info["states"] = data.get("states") or []
        info["exit_states"] = data.get("exit_states") or []
    elif kind == "artifact":
        info["owner_module"] = data.get("owner_module")
        info["format"] = data.get("format")
        info["produced_by"] = (data.get("provenance") or {}).get("produced_by")
        info["consumers"] = data.get("consumers") or []
    elif kind == "error":
        info["category"] = data.get("category")
        info["message"] = data.get("message")
    elif kind == "type":
        info["type_kind"] = data.get("kind")
        if data.get("kind") == "entity":
            info["fields"] = list((data.get("fields") or {}).keys())
        elif data.get("kind") == "enum":
            info["values"] = data.get("values")
    elif kind == "constant":
        info["type"] = data.get("type")
        info["value"] = data.get("value")
    elif kind == "external_schema":
        info["provider"] = data.get("provider")
        info["base_url"] = data.get("base_url")
        info["auth_method"] = data.get("auth_method")
