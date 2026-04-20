"""`forge update` — refresh init-managed project assets in place."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cli.commands import init as init_cmd

NAME = "update"
HELP = "Refresh init-managed project assets to the current Forge version."
DESCRIPTION = (
    "Refreshes the same project-managed assets that `forge init` lays down: "
    "the spec directory structure, schema template symlinks, and project-local "
    "skill symlinks. This command does not overwrite authored spec YAML files. "
    "After refresh, it prints the recommended forge-audit follow-up."
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "--spec-subdir", default=".forge",
        help="Relative path from project root for the spec directory. Default: .forge",
    )
    p.add_argument(
        "--skip-skills", action="store_true",
        help="Skip project-local skill symlink refresh.",
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    project_root = Path.cwd()
    spec_dir = project_root / args.spec_subdir

    if spec_dir.exists() and not spec_dir.is_dir():
        print(f"error: spec path exists and is not a directory: {spec_dir}", file=sys.stderr)
        return 1
    if not spec_dir.exists():
        print(
            f"error: no forge project detected at {spec_dir}/. "
            "Run `forge init` first, or pass --spec-subdir if your project uses a custom spec dir.",
            file=sys.stderr,
        )
        return 1

    try:
        forge_repo, skills_src = init_cmd._resolve_forge_sources()
    except FileNotFoundError as e:
        lines = str(e).splitlines()
        print(f"error: {lines[0]}", file=sys.stderr)
        for line in lines[1:]:
            print(line, file=sys.stderr)
        return 1

    print()
    print(init_cmd._color(init_cmd._FIRE_PRIMARY, "▸ ") + init_cmd._bold("Forge update ") + init_cmd._dim(f"in {project_root}"))
    print()

    ok = init_cmd._color(init_cmd._OK_GREEN, "✓")

    init_cmd._ensure_spec_structure(project_root, spec_dir, ok=ok)
    init_cmd._install_schema_templates(spec_dir, forge_repo, force=True, ok=ok)

    if not args.skip_skills:
        init_cmd._install_skill_symlinks(project_root, skills_src, force=True, ok=ok)

    print()
    print(init_cmd._divider("Next step"))
    print()
    print(init_cmd._dim("  Run a compliance pass against the refreshed project:"))
    print(f"    {init_cmd._bold(init_cmd._color(init_cmd._FIRE_PRIMARY, '/forge-audit'))}")
    print(f"    {init_cmd._bold('\"Audit the specs before implementation\"')}")
    print()

    return 0
