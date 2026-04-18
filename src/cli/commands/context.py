"""`forge context <id>` — build a full context bundle."""

from __future__ import annotations

import argparse
import sys

from cli import bundle as bundle_mod
from cli import common
from cli import index as index_mod
from cli import walker

NAME = "context"
HELP = "Build a full implementation-ready context bundle for an id."
DESCRIPTION = (
    "Walks the spec dependency graph from <id> and emits everything "
    "an agent needs to implement it: the target spec, referenced L0 "
    "entries (sliced, not the whole registry), the owning module, "
    "applicable policies, L1 conventions, L4 callers with derived "
    "implications, and L5 operations."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "id",
        help="Target id. Must be an atom, module, journey, flow, or artifact.",
    )
    common.add_spec_dir_arg(p)
    p.add_argument(
        "--format", choices=["yaml", "json", "markdown"], default="yaml",
        help=(
            "Output format. yaml (default) is most token-efficient. "
            "json is most parseable. markdown wraps each section in a "
            "heading + code block for pasting into a chat."
        ),
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    try:
        index_mod.classify(idx, args.id)
    except (KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        common.suggest_similar(idx, args.id)
        return 1

    bundle, unresolved = walker.walk(idx, args.id)
    output = bundle_mod.render(bundle, fmt=args.format)
    sys.stdout.write(output)

    if unresolved:
        seen: set[str] = set()
        uniq = [u for u in unresolved if not (u in seen or seen.add(u))]
        print(f"\n# Unresolved references ({len(uniq)}):", file=sys.stderr)
        for u in uniq:
            print(f"#   - {u}", file=sys.stderr)
        return 2

    return 0
