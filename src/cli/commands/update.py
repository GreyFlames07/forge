"""`forge update` — refresh init-managed project assets in place."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cli.commands import init as init_cmd

NAME = "update"
HELP = "Refresh init-managed project assets to the current Forge version."
DESCRIPTION = (
    "Refreshes the framework.yaml that `forge init` lays down with the version "
    "bundled in the currently-installed forge package. Does not overwrite authored "
    "spec YAML files. Run after upgrading the forge CLI to pick up updated enums "
    "and built-in vocabulary."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "--spec-dir", default="spec",
        help="Relative path from project root for the spec directory. Default: spec",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Overwrite framework.yaml even if it already exists.",
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    spec_dir = project_root / args.spec_dir

    if spec_dir.exists() and not spec_dir.is_dir():
        print(f"error: spec path exists and is not a directory: {spec_dir}", file=sys.stderr)
        return 1
    if not spec_dir.exists():
        print(
            f"error: no Forge project detected at {spec_dir}/. "
            "Run `forge init` first, or pass --spec-dir if your project uses a custom spec dir.",
            file=sys.stderr,
        )
        return 1

    # Require at least conception.yaml or framework.yaml to confirm it's a forge project.
    markers = [spec_dir / m for m in init_cmd._EXISTING_MARKERS]
    if not any(m.exists() for m in markers):
        print(
            f"error: {spec_dir}/ exists but does not look like a Forge project "
            "(missing conception.yaml and framework.yaml). Run `forge init` first.",
            file=sys.stderr,
        )
        return 1

    ok = init_cmd._color(init_cmd._OK_GREEN, "✓")

    print()
    print(init_cmd._color(init_cmd._FIRE_PRIMARY, "▸ ") + init_cmd._bold("Forge update ") + init_cmd._dim(f"in {project_root}"))
    print()

    init_cmd._install_framework(spec_dir, force=args.force, ok=ok)

    print()
    init_cmd._install_skills(force=args.force, ok=ok)

    print()
    print(init_cmd._divider("Done"))
    print()
    print(init_cmd._dim("  Validate to confirm spec is still clean:"))
    print(f"    {init_cmd._bold('forge validate')}")
    print()

    return 0
