from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

from cli.commands.base import add_project_dir_arg
from cli.crawler import crawl_project
from cli.yaml_io import dump_yaml


def register_knowledge(subparsers) -> None:
    parser = subparsers.add_parser("knowledge", help="List Forge knowledge-layer Markdown docs")
    parser.add_argument("action", nargs="?", choices=["list"], default="list", help="Knowledge action")
    add_project_dir_arg(parser)
    parser.add_argument("--ref", help="Filter by Forge ref, such as container:backend_api or flow:create_note")
    parser.add_argument("--type", dest="type_", help="Filter by knowledge type, such as runbook or test_suite")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--format", choices=["json", "yaml", "md"], default="md")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    root = Path(args.project_dir).resolve() if args.project_dir else Path.cwd()
    docs = _filter_docs(crawl_project(root).to_dict().get("knowledge", []), args)
    payload = {"schema": "forge.knowledge_list", "knowledge": docs, "summary": {"knowledge": len(docs)}}
    if args.format == "json":
        print(json.dumps(payload, indent=2))
    elif args.format == "yaml":
        print(dump_yaml(payload).rstrip())
    else:
        print(_to_markdown(payload))
    return 0


def _filter_docs(docs: Any, args: Namespace) -> list[dict[str, Any]]:
    if not isinstance(docs, list):
        return []
    filtered = [doc for doc in docs if isinstance(doc, dict)]
    if args.ref:
        filtered = [doc for doc in filtered if args.ref in doc.get("refs", [])]
    if args.type_:
        filtered = [doc for doc in filtered if doc.get("type") == args.type_]
    if args.tag:
        filtered = [doc for doc in filtered if args.tag in doc.get("tags", [])]
    return filtered


def _to_markdown(payload: dict[str, Any]) -> str:
    docs = payload["knowledge"]
    lines = ["# Forge Knowledge", "", f"- docs: `{len(docs)}`"]
    if not docs:
        return "\n".join(lines)
    lines.append("")
    for doc in docs:
        title = doc.get("title") or doc.get("path")
        lines.append(f"## {title}")
        lines.append(f"- path: `{doc.get('path')}`")
        if doc.get("type"):
            lines.append(f"- type: `{doc['type']}`")
        if doc.get("refs"):
            lines.append("- refs: " + ", ".join(f"`{ref}`" for ref in doc["refs"]))
        if doc.get("tags"):
            lines.append("- tags: " + ", ".join(f"`{tag}`" for tag in doc["tags"]))
        if doc.get("excerpt"):
            lines.extend(["", str(doc["excerpt"])])
        lines.append("")
    return "\n".join(lines).rstrip()
