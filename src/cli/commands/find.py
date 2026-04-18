"""`forge find <query>` — substring search across entity IDs and descriptions.

Used as the scanning primitive for reuse-before-create probes in the
forge-discover and forge-decompose skills. Agents call this before writing
a new module / atom / type / error to surface potential matches, then
present them advisorily to the human.
"""

from __future__ import annotations

import argparse
import sys

from cli import common

NAME = "find"
HELP = "Search for entities whose ID or description matches a query."
DESCRIPTION = (
    "Case-insensitive substring search across every entity in the spec "
    "directory. Matches on ID (atom/module/type/error name) and on "
    "description. Ranked output: entities matching on both ID and "
    "description rank above single-match hits. Ties break by kind "
    "priority (atoms/modules first) then alphabetical."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "query",
        help="Search string. Case-insensitive substring match.",
    )
    p.add_argument(
        "--kind", choices=common.ALL_KINDS, default=None,
        help="Restrict results to a single kind (atom, module, type, error, etc.).",
    )
    p.add_argument(
        "--limit", type=int, default=10,
        help="Maximum number of matches to show. Default 10. Use 0 for no limit.",
    )
    common.add_spec_dir_arg(p)
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    idx, rc = common.load_index(args.spec_dir)
    if rc != 0:
        return rc

    if not args.query.strip():
        print("error: query must be non-empty", file=sys.stderr)
        return 1

    query_lower = args.query.lower()
    kind_priority = {k: i for i, k in enumerate(common.ALL_KINDS)}

    matches: list[tuple[int, int, str, str, list[str], str]] = []
    # tuple shape: (-score, kind_priority, id, kind, signals, description)

    for entry in idx.entries.values():
        if args.kind and entry.kind != args.kind:
            continue

        id_match = query_lower in entry.id.lower()
        description = common.full_description(entry.data)
        desc_match = bool(description) and query_lower in description.lower()

        if not (id_match or desc_match):
            continue

        signals: list[str] = []
        if id_match:
            signals.append("id")
        if desc_match:
            signals.append("desc")
        score = len(signals)

        matches.append((
            -score,                                  # primary: higher score first (neg for asc sort)
            kind_priority.get(entry.kind, 999),      # secondary: bundleable kinds first
            entry.id,                                # tertiary: alphabetical
            entry.kind,
            signals,
            description,
        ))

    matches.sort()

    total = len(matches)
    if total == 0:
        print(f"# forge find {args.query!r} — no matches")
        return 0

    limit = args.limit if args.limit > 0 else total
    shown = min(total, limit)

    header = f"# forge find {args.query!r} — {total} match{'es' if total != 1 else ''}"
    if shown < total:
        header += f" (showing top {shown})"
    print(header)
    print()

    # Column widths from the subset we'll actually render.
    subset = matches[:shown]
    id_width = max(len(m[2]) for m in subset)
    kind_width = max(len(m[3]) for m in subset)

    for _, _, entity_id, kind, signals, description in subset:
        signal_str = f"[{'+'.join(signals)}]"
        desc_preview = _preview(description, 80)
        print(f"  {entity_id:<{id_width}}  {kind:<{kind_width}}  {signal_str:<10}  {desc_preview}")

    return 0


def _preview(text: str, max_chars: int) -> str:
    if not text:
        return ""
    text = " ".join(text.strip().split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."
