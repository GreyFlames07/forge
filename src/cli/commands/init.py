"""`forge init` — scaffold a new Forge project in the current directory.

Creates the spec directory layout and symlinks the agent skills from the
forge install into this project's skill-discovery paths so Claude Code,
VS Code Copilot, and Codex can all find them.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import cli

# --- Intro animation (adapted from the hammer-cli forge-fire banner) -------

_RESET = "\033[0m"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_ORANGE = 208
_BANNER_TEXT = "INITIALISING FORGE"
_SPARKS = [(238, "·"), (166, ":"), (172, "•"), (202, "*"), (_ORANGE, "✦")]
_FIRE = [160, 166, 172, 178, 184, 220, 214, 208, 202]

# Extended palette for init output (reusing fire tones for continuity).
_FIRE_PRIMARY = 208   # main warm highlight
_FIRE_SOFT = 220      # lighter amber, section dividers
_FIRE_DEEP = 166      # deeper red-orange, marker/arrow
_OK_GREEN = 34        # forest green for ✓ (softer than default bright green)
_META = 245           # soft gray for paths + meta info


def _styled() -> bool:
    """True when stdout supports ANSI output."""
    import os
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _color(code: int, text: str) -> str:
    if not _styled():
        return text
    return f"\033[38;5;{code}m{text}{_RESET}"


def _bold(text: str) -> str:
    if not _styled():
        return text
    return f"\033[1m{text}{_RESET}"


def _dim(text: str) -> str:
    if not _styled():
        return text
    return f"\033[2m{text}{_RESET}"


def _divider(label: str) -> str:
    """Section divider: ── label ──, fire-orange colored."""
    bar = "─" * 5
    return _color(_FIRE_DEEP, bar + " ") + _bold(_color(_FIRE_PRIMARY, label)) + _color(_FIRE_DEEP, " " + bar)


def _fire_text(visible: int, shift: int) -> str:
    size = len(_FIRE)
    return "".join(
        _color(_FIRE[(i + shift) % size], ch) if i < visible else " "
        for i, ch in enumerate(_BANNER_TEXT)
    )


def _play_banner() -> None:
    """Ember-sparks → progressive reveal → fire flicker, once."""
    text_len = len(_BANNER_TEXT)
    columns, _lines = shutil.get_terminal_size((80, 24))
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

NAME = "init"
HELP = "Scaffold a new Forge project in the current directory."
DESCRIPTION = (
    "Creates the spec directory layout (.forge/ with L-layer subdirs) "
    "symlinks the 12 schema template files from the forge source into "
    ".forge/templates/ for in-project reference, and symlinks the forge "
    "agent skills into .claude/skills/ (Claude Code), .codex/skills/ "
    "(OpenAI Codex CLI), and .agents/skills/ (agentskills.io clients — "
    "VS Code Copilot, Cursor). Run in a new or empty project directory "
    "to bootstrap."
)

# Skills to symlink. Must match the set installed into the forge source's
# .agents/skills/ directory.
SKILL_NAMES = (
    "forge-discover",
    "forge-decompose",
    "forge-atom",
    "forge-audit",
    "forge-implement",
    "forge-test-writer",
    "forge-implementer",
)

# Subdirectories created under the spec dir. Empty at init; populated by
# subsequent skill runs (discover writes L2_modules; decompose writes L3_atoms;
# etc.).
SPEC_SUBDIRS = (
    "L2_modules",
    "L2_policies",
    "L3_atoms",
    "L3_artifacts",
    "L4_flows",
    "L4_journeys",
)

# Markers that indicate an existing forge project (refuse to init over unless --force).
EXISTING_PROJECT_MARKERS = (
    "discovery-notes.md",
    "L0_registry.yaml",
    "L1_conventions.yaml",
    "L5_operations.yaml",
)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(NAME, help=HELP, description=DESCRIPTION)
    p.add_argument(
        "--spec-subdir", default=".forge",
        help="Relative path from project root for the spec directory. Default: .forge",
    )
    p.add_argument(
        "--skip-skills", action="store_true",
        help="Skip skill symlink creation.",
    )
    p.add_argument(
        "--force", action="store_true",
        help="Overwrite existing symlinks and proceed over existing projects.",
    )
    p.add_argument(
        "--no-banner", action="store_true",
        help="Skip the init banner animation.",
    )
    p.set_defaults(handler=run)


def run(args: argparse.Namespace) -> int:
    # Banner animation: only when stdout is a terminal, and only if not suppressed.
    if sys.stdout.isatty() and not args.no_banner:
        _play_banner()

    project_root = Path.cwd()
    spec_dir = project_root / args.spec_subdir

    # Resolve forge source from the installed cli package location.
    cli_dir = Path(cli.__file__).resolve().parent
    forge_repo = cli_dir.parent.parent  # src/cli/ -> src/ -> repo root
    skills_src = forge_repo / ".agents" / "skills"

    if not skills_src.is_dir():
        print(f"error: cannot locate forge skills at {skills_src}", file=sys.stderr)
        print("Forge CLI may not be installed in editable mode. From the forge repo root:", file=sys.stderr)
        print("  uv pip install -e .", file=sys.stderr)
        return 1

    # Refuse to init over an existing project unless --force.
    existing = [spec_dir / m for m in EXISTING_PROJECT_MARKERS]
    if any(p.exists() for p in existing) and not args.force:
        print(f"error: existing forge project detected at {spec_dir}/", file=sys.stderr)
        print("Use --force to init over it (will not overwrite existing spec files).", file=sys.stderr)
        return 1

    print()
    print(_color(_FIRE_PRIMARY, "▸ ") + _bold("Forge init ") + _dim(f"in {project_root}"))
    print()

    ok = _color(_OK_GREEN, "✓")
    spec_rel = spec_dir.relative_to(project_root)

    # Step 1: spec directory structure.
    spec_dir.mkdir(parents=True, exist_ok=True)
    print(f"  {ok} {_bold(str(spec_rel) + '/')}")
    for sub in SPEC_SUBDIRS:
        d = spec_dir / sub
        d.mkdir(exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("")
    print(f"  {ok} {len(SPEC_SUBDIRS)} spec subdirectories "
          + _dim("(L2_modules, L2_policies, L3_atoms, L3_artifacts, L4_flows, L4_journeys)"))

    # Step 2: symlink schema templates into .forge/templates/ for in-project reference.
    _install_schema_templates(spec_dir, forge_repo, force=args.force, ok=ok)

    # Step 3: symlink skills.
    if not args.skip_skills:
        _install_skill_symlinks(project_root, skills_src, force=args.force, ok=ok)

    # Step 4: next steps section.
    print()
    print(_divider("Next steps"))
    print()
    print(_dim("  Set the spec dir ") + _dim("(add to your shell rc to persist):"))
    print(f"    {_bold('export FORGE_SPEC_DIR=' + str(spec_dir))}")
    print()
    print(_dim("  Start a session in this directory:"))
    print(f"    {_bold(_color(_FIRE_PRIMARY, 'claude'))}  "
          + _dim("│ ") + f"{_bold(_color(_FIRE_PRIMARY, 'codex'))}  "
          + _dim("│ ") + _dim("any agentskills.io client (VS Code Copilot, Cursor)"))
    print()
    print(_dim("  Trigger a forge skill with a natural-language prompt:"))
    print(f"    {_bold('“I want to build a tool that does X”')}")
    print(f"    {_bold('“Decompose the PAY module into atoms”')}")
    print(f"    {_bold('“Audit the specs before implementation”')}")
    print()
    print(_dim("  Claude Code also supports slash-command shortcuts:"))
    print(f"    {_color(_FIRE_PRIMARY, '/forge-discover')}  "
          + _color(_FIRE_PRIMARY, "/forge-decompose")  + "  "
          + _color(_FIRE_PRIMARY, "/forge-atom")       + "  "
          + _color(_FIRE_PRIMARY, "/forge-audit")      + "  "
          + _color(_FIRE_PRIMARY, "/forge-implement"))
    print()

    return 0


def _install_schema_templates(spec_dir: Path, forge_repo: Path, *, force: bool, ok: str) -> None:
    """Symlink every schema/guide template from src/templates/L*/ into
    <spec_dir>/templates/ (flat). Templates travel with the forge version —
    broken symlinks after a forge repo move are a clear signal to re-run
    `forge init --force`.
    """
    templates_src = forge_repo / "src" / "templates"
    templates_dest = spec_dir / "templates"

    if not templates_src.is_dir():
        print(f"  {_color(160, '✗')} templates source missing at {templates_src}; skipping")
        return

    templates_dest.mkdir(exist_ok=True)

    linked = 0
    skipped = 0
    for layer_dir in sorted(templates_src.iterdir()):
        if not layer_dir.is_dir():
            continue
        for template in sorted(layer_dir.iterdir()):
            if template.suffix != ".md":
                continue
            dest = templates_dest / template.name
            if dest.is_symlink() or dest.exists():
                if force and (dest.is_symlink() or dest.is_file()):
                    dest.unlink()
                else:
                    skipped += 1
                    continue
            dest.symlink_to(template.resolve())
            linked += 1

    templates_rel = templates_dest.relative_to(spec_dir.parent)
    print(f"  {ok} {linked} schema templates " + _dim(f"→ {templates_rel}/"))
    if skipped:
        print(_dim(f"    ({skipped} already present; use --force to recreate)"))


def _install_skill_symlinks(project_root: Path, skills_src: Path, *, force: bool, ok: str) -> None:
    """Symlink every known skill into the discovery paths used by Claude Code,
    Codex CLI, and agentskills.io clients (Copilot, Cursor, VS Code).
    """
    dest_parents = [
        project_root / ".claude" / "skills",   # Claude Code
        project_root / ".codex"  / "skills",   # OpenAI Codex CLI
        project_root / ".agents" / "skills",   # agentskills.io (Copilot, Cursor, ...)
    ]
    for parent in dest_parents:
        parent.mkdir(parents=True, exist_ok=True)

    linked = 0
    skipped = 0
    missing = 0

    for name in SKILL_NAMES:
        src = skills_src / name
        if not src.is_dir():
            missing += 1
            print(f"  {_color(160, '✗')} skill source missing: {src}")
            continue

        for dest_parent in dest_parents:
            dest = dest_parent / name
            if dest.is_symlink() or dest.exists():
                if force:
                    if dest.is_symlink() or dest.is_file():
                        dest.unlink()
                    else:
                        # Directory exists (not a symlink); refuse to remove.
                        skipped += 1
                        print(_dim(f"  - {dest} is a real directory; not touching"))
                        continue
                else:
                    skipped += 1
                    continue
            dest.symlink_to(src)
            linked += 1

    total_attempted = len(SKILL_NAMES) * len(dest_parents)
    print(f"  {ok} {linked}/{total_attempted} skill symlinks "
          + _dim("→ .claude/skills/, .codex/skills/, .agents/skills/"))
    if skipped:
        print(_dim(f"    ({skipped} already present; use --force to recreate)"))
    if missing:
        print(_dim(f"    ({missing} skills missing from source)"))
