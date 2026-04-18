"""`forge list [--kind]` — enumerate ids in the spec directory."""

from __future__ import annotations

import argparse

from cli import common
from cli import index as index_mod

NAME = "list"
HELP = "Enumerate ids present in the spec directory."
DESCRIPTION = (
    "Lists every id in the spec dir, optionally filtered by kind. "
    "With no --kind, groups output by kind."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "--kind", choices=common.ALL_KINDS, default=None,
        help="Restrict output to a single kind.",
    )
    common.add_spec_dir_arg(p)
    p.add_argument(
        "--ids-only", action="store_true",
        help="Emit just the ids, one per line — suitable for piping.",
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    if args.kind:
        entries = sorted(idx.by_kind(args.kind), key=lambda e: e.id)
        if args.ids_only:
            for e in entries:
                print(e.id)
        else:
            print(f"# {args.kind} ({len(entries)})")
            for e in entries:
                desc = common.one_line_description(e.data)
                suffix = f"  — {desc}" if desc else ""
                print(f"  {e.id}{suffix}")
        return 0

    grouped: dict[str, list[index_mod.Entry]] = {}
    for e in idx.entries.values():
        grouped.setdefault(e.kind, []).append(e)

    if args.ids_only:
        for kind in common.ALL_KINDS:
            for e in sorted(grouped.get(kind, []), key=lambda x: x.id):
                print(e.id)
        return 0

    print(f"# Spec dir: {idx.spec_dir}")
    print(f"# Total entries: {sum(len(v) for v in grouped.values())}")
    for kind in common.ALL_KINDS:
        entries = sorted(grouped.get(kind, []), key=lambda x: x.id)
        if not entries:
            continue
        print()
        print(f"# {kind} ({len(entries)})")
        for e in entries:
            desc = common.one_line_description(e.data)
            suffix = f"  — {desc}" if desc else ""
            print(f"  {e.id}{suffix}")
    return 0
