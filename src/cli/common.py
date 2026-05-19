from __future__ import annotations

from pathlib import Path

REQUIRED_ROOT_FILES = ("system.yaml", "runtime.yaml")


def is_forge_root(path: Path) -> bool:
    return path.is_dir() and all((path / filename).exists() for filename in REQUIRED_ROOT_FILES)


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if is_forge_root(current):
        return current
    for candidate in current.parents:
        if is_forge_root(candidate):
            return candidate
    raise FileNotFoundError(
        "Could not find a Forge project root. Run this inside a project root containing "
        "`system.yaml` and `runtime.yaml`, or pass `--project-dir`."
    )
