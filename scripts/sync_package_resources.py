from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_ROOT = REPO_ROOT / "src" / "cli" / "resources"

MANAGED_DOC_FILES = (
    "FRAMEWORK_V4.md",
    "SCHEMA_REFERENCE_V4.md",
)

DOC_FILES = (
    "FRAMEWORK_V4.md",
    "SCHEMA_REFERENCE_V4.md",
)

SKILL_NAMES = (
    "forge-orchestrator",
    "forge-build",
    "forge-business",
    "forge-hydrate",
    "forge-review",
    "forge-schema",
    "forge-security",
)

IGNORED_NAMES = {
    ".DS_Store",
    "__pycache__",
    "coding_agent_skills_reference",
}

IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def main() -> int:
    sync_docs()
    sync_skills()
    return 0


def sync_docs() -> None:
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    for filename in MANAGED_DOC_FILES:
        target = RESOURCE_ROOT / filename
        if filename not in DOC_FILES and target.exists():
            target.unlink()
    for filename in DOC_FILES:
        source = REPO_ROOT / filename
        if source.exists():
            shutil.copy2(source, RESOURCE_ROOT / filename)


def sync_skills() -> None:
    source_root = REPO_ROOT / "skills"
    target_root = RESOURCE_ROOT / "skills"
    target_root.mkdir(parents=True, exist_ok=True)

    for skill_name in SKILL_NAMES:
        source = source_root / skill_name
        target = target_root / skill_name
        if not source.exists():
            continue
        if target.exists() or target.is_symlink():
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
        shutil.copytree(source, target, symlinks=True, ignore=_ignore_resource)


def _ignore_resource(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        if name in IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES:
            ignored.add(name)
        if name == ".git":
            ignored.add(name)
    return ignored


if __name__ == "__main__":
    raise SystemExit(main())
