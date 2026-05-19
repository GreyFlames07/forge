from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from argparse import Namespace
from importlib.resources import as_file, files
from pathlib import Path

from cli.schema import dump_yaml

COLLECTION_DIRS = [
    "high_level_flows",
    "runtime_flows",
    "data_shapes",
    "persistent_shapes",
    "verticals",
    "containers",
]

SKILL_DIRS = [
    "forge-schema",
    "forge-review",
    "forge-security",
    "forge-build",
]

SKILL_ALIASES = {
    "forge-spec": "forge-schema",
}

SKILL_SURFACES = [
    ".claude/skills",
    ".codex/skills",
    ".agents/skills",
]

DOC_FILES = [
    "SCHEMA_REFERENCE_V3.md",
    "FRAMEWORK_V3.md",
]

ORANGE = "208"
YELLOW = "220"
GOLD = "214"
AMBER = "178"
RED = "166"


def register_init(subparsers) -> None:
    parser = subparsers.add_parser("init", help="Initialize a Forge repository")
    parser.add_argument("--root", default=".", help="Target repository root to scaffold into")
    parser.add_argument("--name", default="Forge Project", help="Human-readable project name")
    parser.add_argument("--id", default="forge_project", help="System id to seed into system.yaml")
    parser.add_argument("--force", action="store_true", help="Allow initializing into an existing non-empty directory")
    parser.add_argument("--no-animation", action="store_true", help="Disable the terminal initialization animation")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    target_root = Path(args.root).expanduser().resolve()
    _prepare_target_root(target_root, force=args.force)

    stop_event: threading.Event | None = None
    animation_thread: threading.Thread | None = None
    if _should_animate(args.no_animation):
        _typewriter_sequence("INITIALISING FORGE")
        stop_event = threading.Event()
        animation_thread = threading.Thread(target=_animate_spinner, args=(stop_event,), daemon=True)
        animation_thread.start()

    try:
        _scaffold_repository(target_root, system_name=args.name, system_id=args.id)
    finally:
        if stop_event is not None:
            stop_event.set()
        if animation_thread is not None:
            animation_thread.join(timeout=1)
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()

    _print_init_summary(target_root=target_root, system_name=args.name, system_id=args.id)
    return 0


def _prepare_target_root(target_root: Path, force: bool) -> None:
    if not target_root.exists():
        target_root.mkdir(parents=True, exist_ok=True)
        return
    if not target_root.is_dir():
        raise FileNotFoundError(f"Target path is not a directory: {target_root}")
    if force:
        return
    if any(target_root.iterdir()):
        raise FileNotFoundError(
            f"Target directory is not empty: {target_root}. Re-run with --force if you want to scaffold into it."
        )


def _should_animate(no_animation: bool) -> bool:
    return (not no_animation) and sys.stdout.isatty()


def _typewriter_sequence(text: str, delay: float = 0.04) -> None:
    orange = "\033[38;5;208m"
    reset = "\033[0m"
    current = ""
    for char in text:
        current += char
        sys.stdout.write(f"\r{orange}. {current}{reset}")
        sys.stdout.flush()
        time.sleep(delay)


def _animate_spinner(stop_event: threading.Event) -> None:
    frames = ["✦", "✶", "✷", "✹", "✺", "✧"]
    color_codes = [88, 124, 160, 166, 202, 208, 214]
    reset = "\033[0m"
    text = "INITIALISING FORGE"
    idx = 0
    while not stop_event.is_set():
        frame = frames[idx % len(frames)]
        rendered = "".join(
            f"\033[38;5;{color_codes[(idx + offset) % len(color_codes)]}m{char}"
            for offset, char in enumerate(text)
        )
        star_color = f"\033[38;5;{color_codes[idx % len(color_codes)]}m"
        sys.stdout.write(f"\r{star_color}{frame} {rendered}{reset}")
        sys.stdout.flush()
        time.sleep(0.18)
        idx += 1


def _supports_color() -> bool:
    return sys.stdout.isatty()


def _color(text: str, code: str, *, bold: bool = False) -> str:
    if not _supports_color():
        return text
    weight = "1;" if bold else ""
    return f"\033[{weight}38;5;{code}m{text}\033[0m"


def _banner(text: str) -> str:
    return _color(f"✦ {text} ✦", ORANGE, bold=True)


def _section(text: str) -> str:
    return _color(f"✶ {text}", YELLOW, bold=True)


def _bullet(text: str, *, accent: str = GOLD) -> str:
    return f"{_color('✷', accent, bold=True)} {text}"


def _step(number: int, title: str, detail: str) -> str:
    head = _color(f"{number}.", RED, bold=True)
    label = _color(title, AMBER, bold=True)
    return f"{head} {label}\n   {detail}"


def _scaffold_repository(target_root: Path, system_name: str, system_id: str) -> None:
    forge_root = target_root / "forge"
    _write_text(target_root / "README.md", _project_readme(system_name))
    _write_text(target_root / ".gitignore", _scaffold_gitignore())
    _write_text(forge_root / "decision_notes.md", "# Decision Notes\n\nRecord meaningful Forge decisions here.\n")

    _write_yaml(forge_root / "system.yaml", _system_seed(system_name, system_id))
    _write_yaml(forge_root / "runtime.yaml", {"schema": "forge.v2.runtime", "runtime": {"containers": [], "relationships": []}})
    _write_yaml(forge_root / "early_state.yaml", {"schema": "forge.v2.early_state", "early_state": []})
    _write_yaml(forge_root / "deployment.yaml", {"schema": "forge.v2.deployment", "deployment": {"environments": []}})

    for directory in COLLECTION_DIRS:
        (forge_root / directory).mkdir(parents=True, exist_ok=True)

    _copy_docs(forge_root)
    _copy_skills(forge_root)
    _rewrite_skill_references(forge_root)
    _create_surface_skills(target_root, forge_root)


def _copy_docs(forge_root: Path) -> None:
    forge_root.mkdir(parents=True, exist_ok=True)
    for filename in DOC_FILES:
        with as_file(files("cli").joinpath("resources", filename)) as source_path:
            shutil.copy2(source_path, forge_root / filename)
    _write_text(forge_root / "USING_FORGE.md", _using_forge_doc())


def _copy_skills(forge_root: Path) -> None:
    target_skills = forge_root / "skills"
    target_skills.mkdir(parents=True, exist_ok=True)
    with as_file(files("cli").joinpath("resources", "skills")) as source_skills:
        for skill_name in SKILL_DIRS:
            shutil.copytree(source_skills / skill_name, target_skills / skill_name, dirs_exist_ok=True)
    for alias, target in SKILL_ALIASES.items():
        _write_text(target_skills / alias / "SKILL.md", _alias_skill_text(alias, f"../{target}/SKILL.md"))


def _rewrite_skill_references(forge_root: Path) -> None:
    for skill_name in SKILL_DIRS:
        skill_path = forge_root / "skills" / skill_name / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        text = text.replace("../../SCHEMA_REFERENCE_V3.md", "../../SCHEMA_REFERENCE_V3.md")
        text = text.replace("../../FRAMEWORK_V3.md", "../../FRAMEWORK_V3.md")
        if "Read before starting:" in text and "../../USING_FORGE.md" not in text:
            text = text.replace(
                "Read before starting:\n",
                "Read before starting:\n\n- `../../USING_FORGE.md`\n",
                1,
            )
        skill_path.write_text(text, encoding="utf-8")


def _create_surface_skills(target_root: Path, forge_root: Path) -> None:
    for surface in SKILL_SURFACES:
        surface_root = target_root / surface
        surface_root.mkdir(parents=True, exist_ok=True)
        for skill_name in SKILL_DIRS:
            _create_surface_skill(surface_root, forge_root, skill_name)
        for alias, target in SKILL_ALIASES.items():
            _create_surface_alias_skill(surface_root, alias, target)


def _create_surface_skill(surface_root: Path, forge_root: Path, skill_name: str) -> None:
    source_skill = forge_root / "skills" / skill_name
    target_skill = surface_root / skill_name

    if target_skill.exists() or target_skill.is_symlink():
        if target_skill.is_symlink() or target_skill.is_file():
            target_skill.unlink()
        else:
            shutil.rmtree(target_skill)
    target_skill.mkdir(parents=True, exist_ok=True)

    for child in source_skill.iterdir():
        if child.name == "SKILL.md":
            continue
        target_child = target_skill / child.name
        if target_child.exists() or target_child.is_symlink():
            if target_child.is_symlink() or target_child.is_file():
                target_child.unlink()
            else:
                shutil.rmtree(target_child)
        target_child.symlink_to(_relative_symlink_target(target_skill, child), target_is_directory=child.is_dir())

    surfaced_skill = _surface_skill_text(source_skill / "SKILL.md")
    (target_skill / "SKILL.md").write_text(surfaced_skill, encoding="utf-8")


def _surface_skill_text(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8")
    return (
        text.replace("../../SCHEMA_REFERENCE_V3.md", "../../../forge/SCHEMA_REFERENCE_V3.md")
        .replace("../../FRAMEWORK_V3.md", "../../../forge/FRAMEWORK_V3.md")
        .replace("../../USING_FORGE.md", "../../../forge/USING_FORGE.md")
    )


def _create_surface_alias_skill(surface_root: Path, alias: str, target: str) -> None:
    alias_root = surface_root / alias
    if alias_root.exists() or alias_root.is_symlink():
        if alias_root.is_symlink() or alias_root.is_file():
            alias_root.unlink()
        else:
            shutil.rmtree(alias_root)
    alias_root.mkdir(parents=True, exist_ok=True)
    _write_text(alias_root / "SKILL.md", _alias_skill_text(alias, f"../{target}/SKILL.md"))


def _relative_symlink_target(link_parent: Path, destination: Path) -> Path:
    return Path(os.path.relpath(destination, start=link_parent))


def _alias_skill_text(alias: str, target_path: str) -> str:
    return f"""---
name: {alias}
description: Backwards-compat alias for `forge-schema`
---

# {alias}

This skill name is kept for backwards compatibility.

Continue with:

- `{target_path}`
"""


def _project_readme(system_name: str) -> str:
    return (
        f"# {system_name}\n\n"
        "Initialized with Forge.\n\n"
        "Forge scaffolds a dedicated `forge/` workspace for the schema, docs, and skills.\n\n"
        "Start with `forge/USING_FORGE.md`. Forge is skills-first: the skills drive "
        "the workflow, and the CLI supplies only the scoped context or artifacts the active skill needs.\n"
    )


def _system_seed(system_name: str, system_id: str) -> dict[str, object]:
    return {
        "schema": "forge.v2.system",
        "system": {
            "id": system_id,
            "purpose": f"Define the purpose of {system_name}.",
            "description": "Replace with a plain-language description of the system.",
            "boundary": "Replace with a plain-language statement of what sits inside the system boundary.",
            "security": "Replace with any global security posture rules that already clearly apply.",
            "actors": [],
            "external_dependencies": [],
        },
    }


def _scaffold_gitignore() -> str:
    return "\n".join(
        [
            ".venv/",
            "__pycache__/",
            "*.py[cod]",
            "*.egg-info/",
            ".pytest_cache/",
            "build/",
            "dist/",
            ".DS_Store",
            "",
        ]
    )


def _print_init_summary(target_root: Path, system_name: str, system_id: str) -> None:
    forge_root = target_root / "forge"
    print(_banner("FORGE INITIALIZED"))
    print(f"Forge initialized at {target_root}")
    print(f"{_color('Location:', YELLOW, bold=True)} {target_root}")
    print("")
    print(_section("Framework"))
    print(_bullet(f"system: {system_name} (`{system_id}`)"))
    print(_bullet(f"repository root: {target_root}"))
    print(_bullet(f"forge workspace: {forge_root}"))
    print(_bullet(f"skills: {forge_root / 'skills'}"))
    print("")
    print(_section("Start With Skills"))
    print(_bullet("primary driver: `forge/skills/forge-schema/SKILL.md`"))
    print(_bullet("pre-build architecture review: `forge/skills/forge-review/SKILL.md`"))
    print(_bullet("pre-build security review: `forge/skills/forge-security/SKILL.md`"))
    print(_bullet("plan and build only after those passes: `forge/skills/forge-build/SKILL.md`"))
    print(_bullet("the CLI supports the active skill; it is not the main workflow", accent=ORANGE))
    print("")
    print(_section("Use Forge In This Order"))
    print(
        _step(
            1,
            "Define the broad truth with `forge-schema`.",
            "Author `forge/system.yaml`, `forge/high_level_flows/`, `forge/early_state.yaml`, and `forge/runtime.yaml` first.",
        )
    )
    print(_step(2, "Split the system into development slices in `verticals/`.", "Keep each vertical thin, buildable, and tied to clear user value."))
    print(
        _step(
            3,
            "Deepen one vertical only.",
            "Add `forge/runtime_flows/`, `forge/data_shapes/`, `forge/persistent_shapes/`, `forge/containers/`, and `forge/deployment.yaml` as needed.",
        )
    )
    print(
        _step(
            4,
            "Run `forge-review` and `forge-security` before building.",
            "Use them as readiness gates to catch drift, bloat, missing references, and security gaps before implementation starts.",
        )
    )
    print(_step(5, "Use `forge-build` only after the slice is reviewable.", "Plan or implement the approved vertical, then validate it end to end."))
    print("")
    print(_section("How To Get The Most Out Of The Framework"))
    print(_bullet("stay broad until the previous layer is clear"))
    print(_bullet("model real runtime boundaries, not imagined ones"))
    print(_bullet("only promote shapes that are reused, persisted, or system-significant"))
    print(_bullet("capture meaningful tradeoffs in `decision_notes.md`"))
    print("")
    print(_section("Read Next"))
    print(_bullet(f"`{forge_root / 'USING_FORGE.md'}`"))
    print(_bullet(f"`{forge_root / 'FRAMEWORK_V3.md'}`"))
    print(_bullet(f"`{forge_root / 'SCHEMA_REFERENCE_V3.md'}`"))
    print("")
    print(_section("CLI Support Workflow"))
    print(_bullet("ask the active skill what scope it needs first", accent=ORANGE))
    print(_bullet(f"broad context: `forge context --project-dir {forge_root} --system --format md`"))
    print(_bullet(f"vertical context: `forge context --project-dir {forge_root} --vertical <id> --format json`"))
    print(_bullet(f"audit dashboard: `forge audit --project-dir {forge_root} --output forge-audit.html`"))


def _using_forge_doc() -> str:
    return """# Using Forge

Forge works best when you move from broad architectural truth to one thin,
buildable vertical at a time.

The Forge-owned schema workspace lives under `forge/`.

## Start With Skills

Forge is **skills-first**. The skills are the main operating surface:

- `forge/skills/forge-schema/SKILL.md`
- `forge/skills/forge-review/SKILL.md`
- `forge/skills/forge-security/SKILL.md`
- `forge/skills/forge-build/SKILL.md`

Use the CLI only to support the active skill:

- `forge context` for scoped context
- `forge audit` for a reviewable HTML artifact

Do not start by pulling broad CLI output. Start by choosing the skill, then ask
for only the narrowest context that skill needs next.

## Use Forge In This Order

1. Define the system:
   - `forge/system.yaml`
   - `forge/high_level_flows/`
   - `forge/early_state.yaml`
   - `forge/runtime.yaml`
2. Derive `forge/verticals/` once the runtime picture is stable.
3. Pick one vertical and deepen only that slice:
   - `forge/runtime_flows/`
   - `forge/data_shapes/`
   - `forge/persistent_shapes/`
   - `forge/containers/`
   - `forge/deployment.yaml`
4. Review and secure that slice before build starts.
5. Build and validate the approved slice before moving on.

## Core Artifacts

- `forge/system.yaml`: purpose, boundary, actors, dependencies, and global security posture
- `forge/runtime.yaml`: the real runtime containers and their relationships
- `forge/early_state.yaml`: the important business things that matter before exact typing
- `forge/high_level_flows/`: business and system flows
- `forge/verticals/`: thin development slices derived from the system
- `forge/runtime_flows/`: how a vertical moves through containers
- `forge/data_shapes/`: promoted reusable payload/state shapes
- `forge/persistent_shapes/`: the persisted subset of data shapes
- `forge/containers/`: internal component structure for important containers
- `forge/deployment.yaml`: environments, nodes, trust boundaries, and operational placement

## Skill Roles

- `forge-schema`: define and refine the architecture
- `forge-review`: catch drift, bloat, and broken references
- `forge-security`: review security posture across system, runtime, persistence,
  and deployment
- `forge-build`: plan or implement one vertical with TDD and full-system
  validation

## Recommended Workflow

1. Use `forge-schema` to define the system, flows, early state, and runtime.
2. Initialize `verticals` once the runtime picture is clear.
3. Pick one vertical and deepen only that vertical.
4. Use `forge-review` to catch drift, bloat, and broken references before implementation starts.
5. Use `forge-security` to make the security posture explicit before implementation starts.
6. Use `forge-build` to plan or implement the approved slice.

## Best Operating Mode

- Start with `forge-schema`, not with `forge context`.
- Stay broad until the current layer is genuinely clear.
- Use `forge context` only after the active skill asks for a specific scope.
- Keep `forge audit` as the main artifact for human review and sign-off.
- Record meaningful tradeoffs and scope choices in `forge/decision_notes.md`.

## CLI Usage

Use the CLI to retrieve only the context needed for the current skill step:

- `forge context --project-dir . --system --format md`
- `forge context --project-dir . --vertical <id> --format json`
- `forge context --project-dir . --flow <id> --format md`
- `forge context --project-dir . --container <id> --format yaml`
- `forge context --project-dir . --component <id> --format json`

Start broad, then narrow:

1. vertical
2. flow
3. container
4. component

Use `forge audit --project-dir . --output forge-audit.html` when you want a
reviewable HTML artifact for the whole schema.

## Golden Path Examples

- compact walkthrough: `examples/forge_v2_ordering_example`
- richer reference system: `examples/forge_v2_fulfillment_control_example`

## Anti-Bloat Rules

- Keep one-off payloads inline unless they are reused, persisted, or important enough to deserve a stable name.
- Do not invent containers unless they are real runtime boundaries.
- Do not create container internals unless a container truly needs explicit internal modeling.
- Do not drift deployment into low-level infrastructure configuration.
- Keep the current vertical thin and runnable.
"""


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(payload), encoding="utf-8")
