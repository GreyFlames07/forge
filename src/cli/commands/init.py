"""`forge init` — scaffold a new Forge project in the current directory.

Creates spec/ with framework.yaml (bundled vocabulary) and a blank
conception.yaml stub. The directory layout under spec/ is created by the
user as they build out the spec; init only provides the anchors.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import cli

NAME = "init"
HELP = "Scaffold a new Forge project in the current directory."
DESCRIPTION = (
    "Creates the spec/ directory and copies framework.yaml (the bundled "
    "framework vocabulary: enums, built-in scalars, built-in errors) into it. "
    "Also writes a blank conception.yaml stub. Run in a new or empty project "
    "directory to bootstrap."
)

# Markers that indicate an existing Forge project.
_EXISTING_MARKERS = ("conception.yaml", "framework.yaml")

# --- Banner -------------------------------------------------------------------

_RESET = "\033[0m"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_BANNER_TEXT = "INITIALISING FORGE"
_SPARKS = [(238, "·"), (166, ":"), (172, "•"), (202, "*"), (208, "✦")]
_FIRE = [160, 166, 172, 178, 184, 220, 214, 208, 202]
_FIRE_PRIMARY = 208
_FIRE_DEEP = 166
_OK_GREEN = 34
_META = 245


def _styled() -> bool:
    return sys.stdout.isatty() and not __import__("os").environ.get("NO_COLOR")


def _color(code: int, text: str) -> str:
    return f"\033[38;5;{code}m{text}{_RESET}" if _styled() else text


def _bold(text: str) -> str:
    return f"\033[1m{text}{_RESET}" if _styled() else text


def _dim(text: str) -> str:
    return f"\033[2m{text}{_RESET}" if _styled() else text


def _divider(label: str) -> str:
    bar = "─" * 5
    return _color(_FIRE_DEEP, bar + " ") + _bold(_color(_FIRE_PRIMARY, label)) + _color(_FIRE_DEEP, " " + bar)


def _fire_text(visible: int, shift: int) -> str:
    size = len(_FIRE)
    return "".join(
        _color(_FIRE[(i + shift) % size], ch) if i < visible else " "
        for i, ch in enumerate(_BANNER_TEXT)
    )


def _play_banner() -> None:
    text_len = len(_BANNER_TEXT)
    columns, _ = shutil.get_terminal_size((80, 24))
    clear = " " * max(columns - 1, 0)

    def draw(frame: str, delay: float) -> None:
        sys.stdout.write("\r" + clear + "\r" + frame)
        sys.stdout.flush()
        time.sleep(delay)

    sys.stdout.write(_HIDE_CURSOR)
    try:
        for code, spark in _SPARKS:
            draw(_color(code, spark) + " " + (" " * text_len), 0.07)
        for count in range(1, text_len + 1):
            draw(
                _color(_FIRE[count % len(_FIRE)], "✦") + " " + _fire_text(count, count),
                0.065 if count < text_len else 0.16,
            )
        for shift in range(len(_FIRE) * 2):
            draw(
                _color(_FIRE[shift % len(_FIRE)], "✦") + " " + _fire_text(text_len, shift),
                0.08,
            )
    finally:
        sys.stdout.write(_RESET + _SHOW_CURSOR + "\n")
        sys.stdout.flush()


# --- Scaffold -----------------------------------------------------------------

_CONCEPTION_STUB = """\
id: <conception>
type: conception
name: <ConceptionName>
description: <one-sentence description>
status: draft
owner: <team or individual>
intent: >
  <multi-line statement of what this conception aims to achieve
  and the constraints that define it>
systems: []
actors: []
glossary: []
policies: []
"""


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "--spec-subdir", default="spec",
        help="Relative path from project root for the spec directory. Default: spec",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files and proceed over existing projects.",
    )
    p.add_argument(
        "--no-banner", action="store_true",
        help="Skip the init banner animation.",
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    if sys.stdout.isatty() and not args.no_banner:
        _play_banner()

    project_root = Path.cwd()
    spec_dir = project_root / args.spec_subdir

    # Refuse to init over an existing project unless --force.
    if not args.force:
        for marker in _EXISTING_MARKERS:
            if (spec_dir / marker).exists():
                print(
                    f"error: existing forge project detected at {spec_dir}/",
                    file=sys.stderr,
                )
                print("Use --force to reinitialise.", file=sys.stderr)
                return 1

    print()
    print(_color(_FIRE_PRIMARY, "▸ ") + _bold("Forge init ") + _dim(f"in {project_root}"))
    print()

    ok = _color(_OK_GREEN, "✓")

    # Create spec/ directory.
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_rel = spec_dir.relative_to(project_root)
    print(f"  {ok} {_bold(str(spec_rel) + '/')}")

    # Copy framework.yaml from the bundled CLI package.
    _install_framework(spec_dir, force=args.force, ok=ok)

    # Write blank conception.yaml stub.
    _install_conception(spec_dir, force=args.force, ok=ok)

    print()
    print(_divider("Next steps"))
    print()
    print(_dim("  Edit spec/conception.yaml and replace placeholders:"))
    print(f"    {_bold('id:')}{_dim('  <conception>')}")
    print(f"    {_bold('name:')}{_dim(' <ConceptionName>')}")
    print()
    print(_dim("  Create your first system directory:"))
    print(f"    {_bold('mkdir -p spec/<system>')}")
    print(f"    {_bold('touch spec/<system>/system.yaml')}")
    print()
    print(_dim("  Set the spec dir (add to shell rc to persist):"))
    print(f"    {_bold('export FORGE_SPEC_DIR=\"' + str(spec_dir) + '\"')}")
    print()
    print(_dim("  Validate at any time:"))
    print(f"    {_bold('forge validate')}")
    print()

    return 0


def _install_framework(spec_dir: Path, *, force: bool, ok: str) -> None:
    """Copy the bundled framework.yaml into the spec directory."""
    cli_dir = Path(cli.__file__).resolve().parent
    src = cli_dir / "framework.yaml"
    dest = spec_dir / "framework.yaml"

    if not src.is_file():
        print(f"  {_color(160, '✗')} framework.yaml not found at {src}; skipping")
        return

    if dest.exists() and not force:
        print(_dim(f"  - framework.yaml already present; use --force to overwrite"))
        return

    shutil.copy2(src, dest)
    print(f"  {ok} spec/framework.yaml {_dim('(framework vocabulary)')}")


def _install_conception(spec_dir: Path, *, force: bool, ok: str) -> None:
    """Write a blank conception.yaml stub."""
    dest = spec_dir / "conception.yaml"
    if dest.exists() and not force:
        print(_dim(f"  - conception.yaml already present; use --force to overwrite"))
        return
    dest.write_text(_CONCEPTION_STUB, encoding="utf-8")
    print(f"  {ok} spec/conception.yaml {_dim('(fill in your conception details)')}")
