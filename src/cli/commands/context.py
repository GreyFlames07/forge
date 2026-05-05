"""`forge context <id>` — build a full context bundle."""

from __future__ import annotations

import argparse
import sys

from cli import bundle as bundle_mod
from cli import common
from cli import index as index_mod
from cli import walker

NAME = "context"
HELP = "Build a full implementation-ready context bundle for an element."
DESCRIPTION = (
    "Walks the spec dependency graph from <element-id> and emits everything "
    "an agent needs to implement it: the element (with inline properties and "
    "operations), parent module/domain/system, referenced contracts, types "
    "(transitive), errors, interactions, cascaded policies, and datastores."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "id",
        help="Target element id (e.g. myapp.billing.payments.charge_processor.charge).",
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
