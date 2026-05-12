from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from cli.commands.base import add_forge_dir_arg
from cli.common import find_forge_root
from cli.schema import dump_yaml, load_schema


COLLECTION_MAP = {
    "verticals": "verticals",
    "units": "units",
    "types": "types",
    "operations": "operations",
    "surfaces": "surfaces",
    "stores": "stores",
    "flows": "flows",
}


def register_list(subparsers) -> None:
    parser = subparsers.add_parser("list", help="List schema objects by section")
    add_forge_dir_arg(parser)
    parser.add_argument(
        "collection",
        nargs="?",
        choices=["all", *COLLECTION_MAP.keys(), "verification"],
        default="all",
        help="Section to list. Default: all",
    )
    parser.add_argument(
        "--kind",
        choices=["all", *COLLECTION_MAP.keys(), "verification"],
        help="Alias for the target collection; useful when scripting.",
    )
    parser.add_argument("--vertical", help="Filter items by vertical id where applicable")
    parser.add_argument("--unit", help="Filter items by unit id where applicable")
    parser.add_argument("--format", choices=["text", "yaml", "json"], default="text")
    parser.set_defaults(func=run)


def _matches(item: dict, args: Namespace) -> bool:
    if args.vertical and item.get("vertical") != args.vertical:
        return False
    if args.unit and item.get("unit") != args.unit:
        return False
    return True


def _verification_items(schema) -> list[dict]:
    out: list[dict] = []
    for group, items in schema.verification.items():
        for item in items:
            out.append({"id": f"verification.{group}.{item['id']}", "kind": "verification", "group": group, **item})
    return out


def _emit(payload, output_format: str) -> None:
    if output_format == "yaml":
        print(dump_yaml(payload))
    elif output_format == "json":
        print(json.dumps(payload, indent=2))
    else:
        raise ValueError(f"Unsupported output format: {output_format}")


def _text_section(title: str, items: list[dict]) -> list[str]:
    lines = [f"{title}:"]
    if not items:
        lines.append("- none")
        return lines
    for item in items:
        name = item.get("name")
        label = f"{item['id']}"
        if name and name != item["id"]:
            label += f" :: {name}"
        if item.get("kind") and title != "types":
            label += f" [{item['kind']}]"
        lines.append(f"- {label}")
    return lines


def run(args: Namespace) -> int:
    forge_root = Path(args.forge_dir).resolve() if args.forge_dir else find_forge_root()
    schema = load_schema(forge_root)
    collection = args.kind or args.collection

    if collection == "all":
        payload = {}
        for key, collection_name in COLLECTION_MAP.items():
            payload[key] = [item for item in schema.collections[collection_name] if _matches(item, args)]
        payload["verification"] = [item for item in _verification_items(schema) if _matches(item, args)]
        if args.format in {"yaml", "json"}:
            _emit(payload, args.format)
        else:
            lines: list[str] = []
            for key in ("verticals", "units", "types", "operations", "surfaces", "stores", "flows", "verification"):
                lines.extend(_text_section(key, payload[key]))
                lines.append("")
            print("\n".join(lines).rstrip())
        return 0

    if collection == "verification":
        items = [item for item in _verification_items(schema) if _matches(item, args)]
    else:
        items = [item for item in schema.collections[COLLECTION_MAP[collection]] if _matches(item, args)]

    if args.format in {"yaml", "json"}:
        _emit(items, args.format)
    else:
        print("\n".join(_text_section(collection, items)))
    return 0
