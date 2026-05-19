from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
import shutil

import yaml

from cli.common import ensure_dir, slugify


PROFILES = {
    "full-stack": ["apps/app", "apps/api", "packages/contracts", "packages/types", "infra"],
    "api-service": ["apps/api", "packages/contracts", "packages/types", "infra"],
    "cli-tool": ["apps/cli", "packages/types", "infra"],
    "worker-service": ["apps/worker", "packages/types", "infra"],
}


PROFILE_BLUEPRINTS = {
    "full-stack": {
        "verticals": [
            {
                "id": "core",
                "name": "Core Experience",
                "description": "The first end-user capability path.",
                "purpose": "Deliver the first user-visible working slice.",
                "owned_by": "Replace with owning team or person.",
                "invariants": [],
            }
        ],
        "units": [
            {
                "id": "app",
                "name": "Frontend App",
                "description": "User-facing application shell.",
                "kind": "ui",
                "purpose": "Expose the bootstrap capability to end users.",
                "owned_by": "Replace with owner.",
                "entrypoint": "apps/app/src/main.txt",
                "serves_verticals": ["core"],
                "run": {"dev": "Replace with app dev command", "test": "Replace with app test/build command", "prod": "Replace with app production run/deploy command"},
                "env": [],
                "depends_on": {"units": ["api"], "stores": [], "externals": []},
                "healthcheck": {"kind": "none", "target": ""},
                "promotion": {"independently_promotable": True, "notes": "Static app or frontend deployment."},
            },
            {
                "id": "api",
                "name": "Backend Service",
                "description": "Primary backend runtime for the bootstrap path.",
                "kind": "service",
                "purpose": "Serve the first backend capability and health checks.",
                "owned_by": "Replace with owner.",
                "entrypoint": "apps/api/src/main.txt",
                "serves_verticals": ["core"],
                "run": {"dev": "Replace with API dev command", "test": "Replace with API test command", "prod": "Replace with API production run command"},
                "env": [],
                "depends_on": {"units": [], "stores": ["main"], "externals": []},
                "healthcheck": {"kind": "http", "target": "/health"},
                "promotion": {"independently_promotable": True, "notes": "Primary service runtime."},
            },
        ],
        "stores": [
            {
                "id": "main",
                "name": "Main Transactional Store",
                "description": "Primary canonical operational store.",
                "class": "transactional",
                "dev": "sqlite",
                "test": "sqlite",
                "prod": "postgres",
                "guarantees": {"durability": "durable", "consistency": "strong"},
                "notes": "",
            }
        ],
        "starter_files": {
            "apps/app/README.md": "# App\n\nReplace this with the frontend app runtime.\n",
            "apps/app/src/main.txt": "Bootstrap app entrypoint placeholder.\n",
            "apps/api/README.md": "# API\n\nReplace this with the backend service runtime.\n",
            "apps/api/src/main.txt": "Bootstrap API entrypoint placeholder.\n",
            "packages/contracts/README.md": "# Contracts\n\nShared transport contracts live here.\n",
            "packages/types/README.md": "# Types\n\nShared domain and support types live here.\n",
            "infra/README.md": "# Infra\n\nDeployment and infrastructure files live here.\n",
        },
    },
    "api-service": {
        "verticals": [
            {
                "id": "core",
                "name": "Core API",
                "description": "The first externally useful API capability.",
                "purpose": "Deliver the first working service interaction.",
                "owned_by": "Replace with owning team or person.",
                "invariants": [],
            }
        ],
        "units": [
            {
                "id": "api",
                "name": "API Service",
                "description": "Primary service runtime.",
                "kind": "service",
                "purpose": "Expose the bootstrap API surface.",
                "owned_by": "Replace with owner.",
                "entrypoint": "apps/api/src/main.txt",
                "serves_verticals": ["core"],
                "run": {"dev": "Replace with API dev command", "test": "Replace with API test command", "prod": "Replace with API production run command"},
                "env": [],
                "depends_on": {"units": [], "stores": ["main"], "externals": []},
                "healthcheck": {"kind": "http", "target": "/health"},
                "promotion": {"independently_promotable": True, "notes": "Primary runtime."},
            }
        ],
        "stores": [
            {
                "id": "main",
                "name": "Main Transactional Store",
                "description": "Primary canonical operational store.",
                "class": "transactional",
                "dev": "sqlite",
                "test": "sqlite",
                "prod": "postgres",
                "guarantees": {"durability": "durable", "consistency": "strong"},
                "notes": "",
            }
        ],
        "starter_files": {
            "apps/api/README.md": "# API Service\n\nReplace this with the service runtime.\n",
            "apps/api/src/main.txt": "Bootstrap API entrypoint placeholder.\n",
            "packages/contracts/README.md": "# Contracts\n\nShared transport contracts live here.\n",
            "packages/types/README.md": "# Types\n\nShared domain and support types live here.\n",
            "infra/README.md": "# Infra\n\nDeployment and infrastructure files live here.\n",
        },
    },
    "cli-tool": {
        "verticals": [
            {
                "id": "core",
                "name": "Core CLI",
                "description": "The first useful command workflow.",
                "purpose": "Deliver the first working operator or user command path.",
                "owned_by": "Replace with owning team or person.",
                "invariants": [],
            }
        ],
        "units": [
            {
                "id": "cli",
                "name": "CLI Runtime",
                "description": "Primary command-line runtime.",
                "kind": "cli",
                "purpose": "Expose the bootstrap command path.",
                "owned_by": "Replace with owner.",
                "entrypoint": "apps/cli/src/main.txt",
                "serves_verticals": ["core"],
                "run": {"dev": "Replace with CLI dev command", "test": "Replace with CLI test command", "prod": "Replace with CLI package or run command"},
                "env": [],
                "depends_on": {"units": [], "stores": [], "externals": []},
                "healthcheck": {"kind": "command", "target": "Replace with a bootstrap command health check"},
                "promotion": {"independently_promotable": True, "notes": "CLI distribution runtime."},
            }
        ],
        "stores": [],
        "starter_files": {
            "apps/cli/README.md": "# CLI\n\nReplace this with the command runtime.\n",
            "apps/cli/src/main.txt": "Bootstrap CLI entrypoint placeholder.\n",
            "packages/types/README.md": "# Types\n\nShared support types live here.\n",
            "infra/README.md": "# Infra\n\nPackaging, release, and infra files live here.\n",
        },
    },
    "worker-service": {
        "verticals": [
            {
                "id": "core",
                "name": "Core Worker Capability",
                "description": "The first background-processing capability.",
                "purpose": "Deliver the first useful background workflow.",
                "owned_by": "Replace with owning team or person.",
                "invariants": [],
            }
        ],
        "units": [
            {
                "id": "worker",
                "name": "Worker Runtime",
                "description": "Primary background-processing runtime.",
                "kind": "worker",
                "purpose": "Process the bootstrap background workflow.",
                "owned_by": "Replace with owner.",
                "entrypoint": "apps/worker/src/main.txt",
                "serves_verticals": ["core"],
                "run": {"dev": "Replace with worker dev command", "test": "Replace with worker test command", "prod": "Replace with worker production run command"},
                "env": [],
                "depends_on": {"units": [], "stores": ["main"], "externals": []},
                "healthcheck": {"kind": "process", "target": "Replace with a worker liveness indicator"},
                "promotion": {"independently_promotable": True, "notes": "Background runtime."},
            }
        ],
        "stores": [
            {
                "id": "main",
                "name": "Main Operational Store",
                "description": "Primary store for background processing state.",
                "class": "transactional",
                "dev": "sqlite",
                "test": "sqlite",
                "prod": "postgres",
                "guarantees": {"durability": "durable", "consistency": "strong"},
                "notes": "",
            }
        ],
        "starter_files": {
            "apps/worker/README.md": "# Worker\n\nReplace this with the worker runtime.\n",
            "apps/worker/src/main.txt": "Bootstrap worker entrypoint placeholder.\n",
            "packages/types/README.md": "# Types\n\nShared support types live here.\n",
            "infra/README.md": "# Infra\n\nDeployment and scheduling files live here.\n",
        },
    },
}


def register_init(subparsers) -> None:
    parser = subparsers.add_parser("init", help="Scaffold a Forge V2 project")
    parser.add_argument("--profile", choices=sorted(PROFILES), help="Project profile to scaffold")
    parser.add_argument("--name", help="System name")
    parser.add_argument("--id", help="System id")
    parser.add_argument("--root", default=".", help="Project root to scaffold into")
    parser.add_argument("--no-vendor-assets", action="store_true", help="Do not copy Forge docs/frameworks/skills into the project")
    parser.add_argument(
        "--no-link-skills",
        action="store_true",
        help="Do not link project skills into Claude/Codex/Copilot-compatible home skill scan locations",
    )
    parser.set_defaults(func=run)


def _prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    if value:
        return value
    if default is not None:
        return default
    raise ValueError(f"{text} is required")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


def _write_text(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _asset_root() -> Path:
    return Path(__file__).resolve().parents[1] / "assets"


def _copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for entry in source.iterdir():
        target = destination / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, target)


def _vendor_assets(root: Path) -> None:
    assets = _asset_root()
    docs_src = assets / "docs"
    frameworks_src = assets / "frameworks"
    skills_src = assets / "agents_skills"

    if docs_src.exists():
        _copy_tree_contents(docs_src, root / "docs")
    if frameworks_src.exists():
        _copy_tree_contents(frameworks_src, root / "frameworks")
    if skills_src.exists():
        _copy_tree_contents(skills_src, root / ".agents" / "skills")


def _safe_symlink(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_symlink():
        dest.unlink()
    elif dest.exists():
        return f"skip:{dest}"
    dest.symlink_to(src)
    return f"linked:{dest}"


def _skill_link_targets(home: Path) -> list[Path]:
    targets = [
        home / ".claude" / "skills",
        home / ".codex" / "skills",
        # agentskills.io-compatible clients such as VS Code Copilot and Cursor.
        home / ".agents" / "skills",
    ]
    copilot_root = home / ".copilot"
    if copilot_root.exists():
        targets.append(copilot_root / "skills")
    return targets


def _link_project_skills(root: Path) -> list[str]:
    project_skills = root / ".agents" / "skills"
    if not project_skills.exists():
        return []
    home = Path.home()
    targets = _skill_link_targets(home)
    results: list[str] = []
    for skill_dir in sorted(project_skills.iterdir()):
        if not skill_dir.is_dir():
            continue
        for target_base in targets:
            result = _safe_symlink(skill_dir, target_base / skill_dir.name)
            results.append(result)
    return results


def run(args: Namespace) -> int:
    root = Path(args.root).resolve()
    profile = args.profile or _prompt("Project profile", "full-stack")
    name = args.name or _prompt("System name")
    system_id = args.id or slugify(name)

    forge = ensure_dir(root / "forge")
    blueprint = PROFILE_BLUEPRINTS[profile]
    for section in [
        "verticals",
        "units",
        "types",
        "operations",
        "surfaces",
        "stores",
        "flows",
        "verification/startup",
        "verification/surfaces",
        "verification/flows",
        "workbench",
    ]:
        ensure_dir(forge / section)

    for relative in PROFILES[profile]:
        ensure_dir(root / relative)

    _write_yaml(
        forge / "system.yaml",
        {
            "schema_version": "forge.v2",
            "system": {
                "id": system_id,
                "name": name,
                "project_profile": profile,
                "description": "Replace with a one-sentence system summary.",
                "purpose": "Replace with the system purpose.",
                "goals": ["Replace with the first concrete goal."],
                "invariants": ["Replace with a non-negotiable system truth."],
                "auth_contexts": [{"id": "anonymous", "description": "Unauthenticated caller"}],
                "security": {
                    "posture": ["Replace with a global security rule."],
                    "data_handling": ["Replace with a global data handling rule."],
                },
                "environments": [
                    {"id": "dev", "description": "Local development"},
                    {"id": "prod", "description": "Production deployment"},
                ],
                "promotion_stages": ["dev", "prod"],
            },
        },
    )
    for vertical in blueprint["verticals"]:
        _write_yaml(forge / "verticals" / f"{vertical['id']}.yaml", vertical)
    for unit in blueprint["units"]:
        _write_yaml(forge / "units" / f"{unit['id']}.yaml", unit)
    for store in blueprint["stores"]:
        _write_yaml(forge / "stores" / f"{store['id']}.yaml", store)
    _write_yaml(
        forge / "bootstrap.yaml",
        {
            "bootstrap": {
                "description": "Replace with the first runnable vertical slice for this profile.",
                "required_units": [unit["id"] for unit in blueprint["units"]],
                "required_stores": [store["id"] for store in blueprint["stores"]],
                "required_surfaces": [],
                "path": [],
                "success_criteria": ["Replace with what makes bootstrap count as working."],
                "preserve": True,
            }
        },
    )
    _write_yaml(
        forge / "build_policy.yaml",
        {
            "build_policy": {
                "strategy": "vertical_first",
                "preserve_runnability": True,
                "completion_states": [
                    "specified",
                    "scaffolded",
                    "implemented",
                    "composed",
                    "reachable",
                    "verified",
                ],
                "rules": [
                    "No task may break the bootstrap path.",
                    "Every public surface must reference a canonical operation.",
                    "Every writable canonical type must declare persistence semantics.",
                ],
            }
        },
    )
    _write_yaml(forge / "verification" / "promotion_gates.yaml", {"dev": [], "test": [], "prod": []})
    _write_yaml(
        forge / "workbench" / "status.yaml",
        {
            "bootstrap_health": "unknown",
            "schema_coverage": "initial",
            "implementation_progress": "not_started",
            "validation_state": "not_run",
            "operator_checkpoints": [],
        },
    )
    (forge / "workbench" / "discovery.md").write_text(
        "# Discovery Notes\n\nDocument the reasoning behind system, unit, bootstrap, and security decisions here.\n",
        encoding="utf-8",
    )
    _write_text(
        root / "README.md",
        f"# {name}\n\nThis project was scaffolded by Forge V2 with the `{profile}` profile.\n\nSchema lives under `forge/`.\n",
    )
    _write_text(
        root / ".gitignore",
        ".venv/\n__pycache__/\n.pytest_cache/\nnode_modules/\ndist/\nbuild/\n",
    )
    for relative, contents in blueprint["starter_files"].items():
        _write_text(root / relative, contents)
    if not args.no_vendor_assets:
        _vendor_assets(root)
    link_results: list[str] = []
    if not args.no_link_skills:
        link_results = _link_project_skills(root)
    print(f"Initialized Forge V2 scaffold in {root}")
    print(f"Profile: {profile}")
    if not args.no_vendor_assets:
        print("Vendored Forge docs, frameworks, and agent skills into the project.")
    if not args.no_link_skills:
        linked = len([result for result in link_results if result.startswith("linked:")])
        skipped = len([result for result in link_results if result.startswith("skip:")])
        print(
            "Skill links: "
            f"{linked} linked, {skipped} skipped across Claude, Codex, and Copilot-compatible scan locations."
        )
    print("Next steps: fill in forge/system.yaml, define bootstrap, then use `forge list` and `forge context` to inspect the scaffolded schema.")
    return 0
