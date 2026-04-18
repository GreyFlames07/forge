"""
Shared helpers used by multiple command modules.

Keep this module light: argument decorators, index loading, error
messaging, and text utilities. Anything walker- or bundle-specific
belongs in those modules.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from cli import index as index_mod


# Kind constants used by `list` filter and `inspect` branching.
BUNDLEABLE_KINDS: tuple[str, ...] = ("atom", "module", "journey", "flow", "artifact")
ALL_KINDS: tuple[str, ...] = (
    "atom", "module", "journey", "flow", "artifact",
    "policy", "type", "error", "constant", "external_schema", "marker",
)


# ----------------------------------------------------------------------
# Argparse decorators — standard flags reused by multiple commands.
# ----------------------------------------------------------------------

def add_spec_dir_arg(parser: argparse.ArgumentParser) -> None:
    """Adds the standard --spec-dir flag. Resolution order is documented in
    resolve_spec_dir: --spec-dir > $FORGE_SPEC_DIR > auto-discover."""
    parser.add_argument(
        "--spec-dir", default=None,
        help="Path to spec directory. Overrides $FORGE_SPEC_DIR and auto-discovery.",
    )


# ----------------------------------------------------------------------
# Index loading — wraps resolve + load with stderr error messaging.
# ----------------------------------------------------------------------

def load_index(spec_dir_arg: str | None) -> tuple[index_mod.Index | None, int]:
    """Resolve spec dir and load an Index.

    Returns (index, 0) on success or (None, 1) if resolution/loading fails.
    The error is already printed to stderr by the time 1 is returned, so
    callers can bail with the returned code directly.
    """
    try:
        spec_dir = index_mod.resolve_spec_dir(spec_dir_arg)
        idx = index_mod.load(spec_dir)
        return idx, 0
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return None, 1


# ----------------------------------------------------------------------
# Id suggestion — used by commands that accept an id argument to help
# users recover from typos.
# ----------------------------------------------------------------------

def suggest_similar(idx: index_mod.Index, target: str, limit: int = 5) -> None:
    """Print up to `limit` ids close to `target`, best matches first.

    Scoring prefers ids in the same namespace (shared dot-separated
    prefix) over coincidental substring matches. Writes to stderr.
    Silent if there are no reasonable candidates.
    """
    target_low = target.lower()
    target_parts = target_low.split(".")

    scored: list[tuple[int, str]] = []
    for e in idx.entries.values():
        eid_low = e.id.lower()
        # Score = number of matching leading dot-segments (higher is better).
        eid_parts = eid_low.split(".")
        shared_prefix = 0
        for a, b in zip(target_parts, eid_parts):
            if a == b:
                shared_prefix += 1
            else:
                break
        substring_hit = target_low in eid_low or eid_low in target_low
        if shared_prefix > 0 or substring_hit:
            # Primary key: shared prefix segments; secondary: substring hit.
            score = shared_prefix * 10 + (1 if substring_hit else 0)
            scored.append((score, e.id))

    if not scored:
        return
    scored.sort(key=lambda x: (-x[0], x[1]))
    print("\nDid you mean:", file=sys.stderr)
    for _, candidate in scored[:limit]:
        print(f"  {candidate}", file=sys.stderr)


# ----------------------------------------------------------------------
# Description utilities — used by list and inspect.
# ----------------------------------------------------------------------

def full_description(data: Any) -> str:
    """Full description text (uncapped) — newlines collapsed to spaces."""
    if not isinstance(data, dict):
        return ""
    desc = data.get("description") or data.get("message") or ""
    if not isinstance(desc, str):
        return ""
    return " ".join(desc.strip().split())


def one_line_description(data: Any, max_chars: int = 80) -> str:
    """Compact description capped for table rendering."""
    text = full_description(data)
    if not text:
        return ""
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text
