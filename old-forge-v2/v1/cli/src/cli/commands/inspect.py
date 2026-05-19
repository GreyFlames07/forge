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
    if kind == "conception":
        info["systems"] = data.get("systems") or []
        info["owner"] = data.get("owner")
    elif kind == "system":
        info["domains"] = data.get("domains") or []
        info["platform"] = data.get("platform")
        info["language"] = data.get("language")
        info["deployment"] = data.get("deployment")
        info["policies"] = data.get("policies") or []
    elif kind == "domain":
        info["modules"] = data.get("modules") or []
        info["owner"] = data.get("owner")
        info["policies"] = data.get("policies") or []
    elif kind == "module":
        info["elements"] = data.get("elements") or []
        info["version"] = data.get("version")
        packaging = data.get("packaging") or {}
        info["packaging"] = packaging.get("kind")
        info["runtime"] = packaging.get("runtime")
        info["external_dependencies"] = data.get("external_dependencies") or []
        info["policies"] = data.get("policies") or []
    elif kind == "element":
        info["element_kind"] = data.get("kind")
        info["properties"] = [p.get("id") for p in data.get("properties") or [] if isinstance(p, dict)]
        info["operations"] = [o.get("id") for o in data.get("operations") or [] if isinstance(o, dict)]
        info["relationships"] = data.get("relationships") or []
        info["policies"] = data.get("policies") or []
    elif kind == "type":
        info["type_kind"] = data.get("kind")
        info["base"] = data.get("base")
        info["version"] = data.get("version")
        if data.get("kind") == "composite":
            info["property_count"] = len(data.get("properties") or [])
        constraints = data.get("constraints") or {}
        if constraints:
            info["constraints"] = constraints
    elif kind == "error":
        info["code"] = data.get("code")
        info["http_status"] = data.get("http_status")
    elif kind == "policy":
        info["policy_kind"] = data.get("kind")
        info["owner"] = data.get("owner")
        info["enforcement"] = data.get("enforcement")
    elif kind == "contract":
        info["version"] = data.get("version")
        info["protocol"] = data.get("protocol")
        info["producer"] = data.get("producer")
        info["consumers"] = data.get("consumers") or []
        info["inputs"] = data.get("inputs") or []
        info["outputs"] = data.get("outputs") or []
    elif kind == "integration":
        info["provider"] = data.get("provider")
        info["contract"] = data.get("contract")
        info["auth_mechanism"] = data.get("auth_mechanism")
    elif kind == "interaction":
        info["caller"] = data.get("caller")
        info["callee"] = data.get("callee")
        info["trigger"] = data.get("trigger")
    elif kind == "flow":
        info["trigger"] = data.get("trigger")
        info["step_count"] = len(data.get("steps") or [])
        info["owner"] = data.get("owner")
    elif kind == "constant":
        info["data_type"] = data.get("data_type")
        info["value"] = data.get("value")
    elif kind == "datastore":
        info["storage_kind"] = data.get("kind")
        info["engine"] = data.get("engine")
        info["purpose"] = data.get("purpose")
        info["consumers"] = data.get("consumers") or []
        info["version"] = data.get("version")
    elif kind == "test":
        info["test_kind"] = data.get("kind")
        info["target"] = data.get("target")
    elif kind == "environment":
        info["env_kind"] = data.get("kind")
        info["region"] = data.get("region")
    elif kind == "deployment":
        info["module"] = data.get("module")
        info["environment"] = data.get("environment")
        info["version"] = data.get("version")
        info["deployed_at"] = data.get("deployed_at")
