from __future__ import annotations

import os
import shutil
import sys
import threading
import time
from argparse import Namespace
from importlib.resources import as_file, files
from pathlib import Path

from cli.crawler import DEFAULT_CRAWLER_CONFIG
from cli.yaml_io import dump_yaml

SKILL_DIRS = [
    "forge-business",
    "forge-schema",
    "forge-hydrate",
    "forge-review",
    "forge-security",
    "forge-build",
]

SKILL_SURFACES = [
    ".claude/skills",
    ".codex/skills",
    ".agents/skills",
    ".copilot/skills",
]

DOC_FILES = [
    "SCHEMA_REFERENCE_V4.md",
    "FRAMEWORK_V4.md",
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
    _write_text(target_root / "business-plan.md", _business_plan_doc(system_name))

    _write_v4_schema_files(forge_root, system_name, system_id)
    _copy_docs(forge_root)
    _copy_skills(forge_root)
    _rewrite_skill_references(forge_root)
    _create_surface_skills(target_root, forge_root)
    _create_github_copilot_context(target_root)


def _copy_docs(forge_root: Path) -> None:
    forge_root.mkdir(parents=True, exist_ok=True)
    for filename in DOC_FILES:
        with as_file(files("cli").joinpath("resources", filename)) as source_path:
            shutil.copy2(source_path, forge_root / filename)
    _write_text(forge_root / "USING_FORGE.md", _using_forge_doc())


def _write_v4_schema_files(forge_root: Path, system_name: str, system_id: str) -> None:
    _write_yaml(
        forge_root / "system.yaml",
        {
            "schema": "forge.system",
            "system": {
                "id": system_id,
                "purpose": f"Define the purpose of {system_name}.",
                "description": "Replace with a plain-language description of the system.",
                "boundary": "Replace with what sits inside and outside the system boundary.",
                "security": "Replace with global security posture rules.",
                "actors": [],
                "external_dependencies": [],
                "business_actions": [],
            },
        },
    )
    _write_yaml(
        forge_root / "containers.yaml",
        {
            "schema": "forge.containers",
            "containers": [],
            "container_flows": [],
        },
    )
    _write_yaml(
        forge_root / "entities.yaml",
        {
            "schema": "forge.entities",
            "entities": [],
        },
    )
    _write_yaml(
        forge_root / "decisions.yaml",
        {
            "schema": "forge.decisions",
            "decisions": [],
        },
    )
    _write_yaml(forge_root / "crawler.yaml", DEFAULT_CRAWLER_CONFIG)


def _copy_skills(forge_root: Path) -> None:
    target_skills = forge_root / "skills"
    target_skills.mkdir(parents=True, exist_ok=True)
    with as_file(files("cli").joinpath("resources", "skills")) as source_skills:
        for skill_name in SKILL_DIRS:
            shutil.copytree(source_skills / skill_name, target_skills / skill_name, dirs_exist_ok=True)


def _rewrite_skill_references(forge_root: Path) -> None:
    for skill_name in SKILL_DIRS:
        skill_path = forge_root / "skills" / skill_name / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        text = text.replace("../../SCHEMA_REFERENCE_V4.md", "forge/SCHEMA_REFERENCE_V4.md")
        text = text.replace("../../FRAMEWORK_V4.md", "forge/FRAMEWORK_V4.md")
        text = text.replace("../../USING_FORGE.md", "forge/USING_FORGE.md")
        if "Read before starting:" in text and "forge/USING_FORGE.md" not in text:
            text = text.replace(
                "Read before starting:\n",
                "Read before starting:\n\n- `forge/USING_FORGE.md`\n",
                1,
            )
        skill_path.write_text(text, encoding="utf-8")


def _create_surface_skills(target_root: Path, forge_root: Path) -> None:
    for surface in SKILL_SURFACES:
        surface_root = target_root / surface
        surface_root.mkdir(parents=True, exist_ok=True)
        for skill_name in SKILL_DIRS:
            _create_surface_skill(surface_root, forge_root, skill_name)


def _create_surface_skill(surface_root: Path, forge_root: Path, skill_name: str) -> None:
    source_skill = forge_root / "skills" / skill_name
    target_skill = surface_root / skill_name

    if target_skill.exists() or target_skill.is_symlink():
        if target_skill.is_symlink() or target_skill.is_file():
            target_skill.unlink()
        else:
            shutil.rmtree(target_skill)
    target_skill.symlink_to(_relative_symlink_target(surface_root, source_skill), target_is_directory=True)


def _create_github_copilot_context(target_root: Path) -> None:
    github_root = target_root / ".github"
    instructions_root = github_root / "instructions"
    prompts_root = github_root / "prompts"
    instructions_root.mkdir(parents=True, exist_ok=True)
    prompts_root.mkdir(parents=True, exist_ok=True)
    _write_text(github_root / "copilot-instructions.md", _copilot_instructions_doc())
    _write_text(instructions_root / "forge.instructions.md", _copilot_path_instructions_doc())
    for skill_name in SKILL_DIRS:
        _create_symlink(
            prompts_root / f"{skill_name}.prompt.md",
            target_root / "forge" / "skills" / skill_name / "SKILL.md",
        )


def _create_symlink(link_path: Path, destination: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_symlink() or link_path.is_file():
            link_path.unlink()
        else:
            shutil.rmtree(link_path)
    link_path.symlink_to(_relative_symlink_target(link_path.parent, destination), target_is_directory=destination.is_dir())


def _relative_symlink_target(link_parent: Path, destination: Path) -> Path:
    return Path(os.path.relpath(destination, start=link_parent))


def _project_readme(system_name: str) -> str:
    return (
        f"# {system_name}\n\n"
        "Initialized with Forge.\n\n"
        "Forge scaffolds a dedicated `forge/` workspace for the schema, docs, and skills.\n\n"
        "Start with `forge/USING_FORGE.md`. Forge is skills-first: the skills drive "
        "the workflow, and the CLI supplies only the scoped context or artifacts the active skill needs.\n"
    )


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


def _copilot_instructions_doc() -> str:
    return """# Forge Instructions

This repository uses Forge V4. Start with `forge/USING_FORGE.md`, then use the
skills in `forge/skills` in this order:

1. `forge-business`
2. `forge-schema`
3. `forge-review`
4. `forge-security`
5. `forge-build`

Treat `forge/skills` as the canonical skill source. Agent-specific skill
surfaces are symlinked back to that directory.
"""


def _copilot_path_instructions_doc() -> str:
    return """---
applyTo: "**"
---

Use the Forge V4 workflow for repository work. Read `forge/USING_FORGE.md`
before implementation, and prefer the relevant skill in `forge/skills` for the
current task.
"""


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
    print(_bullet("business discovery: `forge/skills/forge-business/SKILL.md`"))
    print(_bullet("system design: `forge/skills/forge-schema/SKILL.md`"))
    print(_bullet("pre-build architecture review: `forge/skills/forge-review/SKILL.md`"))
    print(_bullet("pre-build security review: `forge/skills/forge-security/SKILL.md`"))
    print(_bullet("plan and build only after those passes: `forge/skills/forge-build/SKILL.md`"))
    print(_bullet("the CLI supports the active skill; it is not the main workflow", accent=ORANGE))
    print("")
    print(_section("Use Forge In This Order"))
    print(
        _step(
            1,
            "Frame the business with `forge-business`, then define C1/C2 with `forge-schema`.",
            "Author `business-plan.md`, then central Forge files: `system.yaml`, "
            "`containers.yaml`, `entities.yaml`, `decisions.yaml`, and `crawler.yaml`.",
        )
    )
    print(_step(2, "Speculate runtime flows before settling containers.", "Use business actions to reason about cross-container control movement."))
    print(
        _step(
            3,
            "Leave C3 beside implementation.",
            "Use `@forge:component`, `@forge:type`, `@forge:persistence`, and `@forge:operation` annotations in code.",
        )
    )
    print(
        _step(
            4,
            "Run `forge-review` and `forge-security` before building.",
            "Use them as readiness gates to catch drift, unclear C3 expectations, missing references, and security gaps.",
        )
    )
    print(_step(5, "Use `forge-build` only after the slice is reviewable.", "Build one thin slice, add annotations, then validate with `forge crawl`."))
    print("")
    print(_section("How To Get The Most Out Of The Framework"))
    print(_bullet("model C1/C2 centrally and C3 beside code"))
    print(_bullet("model real runtime boundaries, not imagined ones"))
    print(_bullet("run `forge crawl` after schema or code annotation changes"))
    print(_bullet("capture meaningful tradeoffs in `forge/decisions.yaml`"))
    print("")
    print(_section("Read Next"))
    print(_bullet(f"`{forge_root / 'USING_FORGE.md'}`"))
    print(_bullet(f"`{forge_root / 'FRAMEWORK_V4.md'}`"))
    print(_bullet(f"`{forge_root / 'SCHEMA_REFERENCE_V4.md'}`"))
    print("")
    print(_section("CLI Support Workflow"))
    print(_bullet("ask the active skill what scope it needs first", accent=ORANGE))
    print(_bullet(f"crawl model: `forge crawl --project-dir {forge_root} --format json`"))
    print(_bullet(f"broad context: `forge context --project-dir {forge_root} --system --format md`"))
    print(_bullet(f"container context: `forge context --project-dir {forge_root} --container <id> --format json`"))
    print(_bullet(f"audit dashboard: `forge audit --project-dir {forge_root} --output forge-audit.html`"))


def _using_forge_doc() -> str:
    return """# Using Forge

Forge V4 keeps central architecture and implementation architecture separate.

The Forge-owned schema workspace lives under `forge/`.

## Start With Skills

Forge is **skills-first**. The skills are the main operating surface:

- `forge/skills/forge-business/SKILL.md`
- `forge/skills/forge-schema/SKILL.md`
- `forge/skills/forge-hydrate/SKILL.md`
- `forge/skills/forge-review/SKILL.md`
- `forge/skills/forge-security/SKILL.md`
- `forge/skills/forge-build/SKILL.md`

Use the CLI only to support the active skill:

- `forge crawl` for the merged V4 model
- `forge context` for scoped context
- `forge audit` for a reviewable HTML artifact

Do not start by pulling broad CLI output. Start by choosing the skill, then ask
for only the narrowest context that skill needs next.

## Use Forge In This Order

1. For new ideas, use `forge-business` to create `business-plan.md`.
2. Define C1/C2 system architecture:
   - `forge/system.yaml`
   - `forge/containers.yaml`
   - `forge/entities.yaml`
   - `forge/decisions.yaml`
   - `forge/crawler.yaml`
3. Use `forge-hydrate` when an existing codebase needs to be reverse-engineered into Forge V4.
4. Use business actions to speculate cross-container runtime flows.
5. Settle runtime containers only after the flow shape is clear.
6. Add C3 annotations beside the implementation:
   - `@forge:component`
   - `@forge:type`
   - `@forge:persistence`
   - `@forge:operation`
7. Run `forge crawl`, `forge context`, and `forge audit` to validate the merged model.

## Core Artifacts

- `business-plan.md`: market research, product framing, MVP sequence, risks, and business actions
- `forge/system.yaml`: purpose, boundary, actors, dependencies, security posture, and business actions
- `forge/containers.yaml`: real runtime containers, deployment entries, and cross-container runtime flows
- `forge/entities.yaml`: important entities, records, lifecycle objects, ownership, persistence, and security notes
- `forge/decisions.yaml`: crawlable decision records for non-trivial architecture, security, review, and build choices
- `forge/crawler.yaml`: source scanning and annotation parsing configuration

## Skill Roles

- `forge-business`: research markets, frame product scenarios, sequence MVP scope, and define business actions
- `forge-schema`: design C1/C2 system architecture and central schema
- `forge-hydrate`: reverse-engineer existing code into Forge V4 schema and C3 annotations
- `forge-review`: review central schema, extracted C3, crawler findings, context, and audit output
- `forge-security`: review security posture across system, runtime, entities, persistence, and operations
- `forge-build`: plan or implement one build slice with code-owned C3 annotations and tests

## Recommended Workflow

1. Use `forge-business` to research the market, frame the product, and define business actions.
2. Use `forge-schema` to define system intent, containers, entities, and runtime flows.
3. Use `forge-review` to catch drift, bloat, broken references, and unclear C3 expectations.
4. Use `forge-security` to make the security posture explicit before implementation starts.
5. Use `forge-build` to plan or implement the approved slice.
6. Run `forge crawl` after code or schema changes to validate the merged model.

## Best Operating Mode

- Start with `forge-business` for new ideas and `forge-schema` for already-validated direction, not with `forge context`.
- Keep C1/C2 central and C3 beside code.
- Use `forge context` only after the active skill asks for a specific scope.
- Keep `forge audit` as the main artifact for human review and sign-off.
- Record meaningful tradeoffs and scope choices in `forge/decisions.yaml`.

## CLI Usage

Use the CLI to retrieve only the context needed for the current skill step:

- `forge crawl --project-dir . --format json`
- `forge context --project-dir . --system --format md`
- `forge context --project-dir . --flow <id> --format md`
- `forge context --project-dir . --container <id> --format yaml`
- `forge context --project-dir . --component <id> --format json`
- `forge context --project-dir . --entity <id> --format json`
- `forge context --project-dir . --operation <id> --format json`
- `forge context --project-dir . --data-shape <id> --format json`

Start broad, then narrow:

1. system
2. flow or container
3. entity, component, operation, or data shape

Use `forge audit --project-dir . --output forge-audit.html` when you want a
reviewable HTML artifact for the merged model.

## Golden Path Examples

- `examples/forge_minimal_web_app`

## Anti-Bloat Rules

- Keep C1/C2 central and C3 beside code.
- Do not invent containers unless they are real runtime boundaries.
- Do not model inside-container flow centrally.
- Do not add distributed-system complexity without a concrete driver.
- Keep the current build slice thin and runnable.
"""


def _business_plan_doc(system_name: str) -> str:
    return f"""# Business Plan: {system_name}

Use `forge-business` to replace this scaffold with market research, product
framing, MVP sequencing, risks, assumptions, and development guidance for
`forge-schema`.

## Executive Summary

TBD

## Market Overview

TBD

## Target Customers

TBD

## Competitors

TBD

## Opportunities

TBD

## Assumptions And Tests

TBD

## MVP Sequence

TBD

## Risks

TBD

## Development Guidance For Forge Schema

TBD

## Sources

TBD
"""


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(payload), encoding="utf-8")
