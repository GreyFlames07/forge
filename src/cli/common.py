from __future__ import annotations

from pathlib import Path

REQUIRED_ROOT_FILES = ("system.yaml", "runtime.yaml")


def is_forge_root(path: Path) -> bool:
    return path.is_dir() and all((path / filename).exists() for filename in REQUIRED_ROOT_FILES)


def _embedded_forge_root(path: Path) -> Path | None:
    candidate = path / "forge"
    if is_forge_root(candidate):
        return candidate
    return None


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if is_forge_root(current):
        return current
    embedded = _embedded_forge_root(current)
    if embedded is not None:
        return embedded
    for candidate in current.parents:
        if is_forge_root(candidate):
            return candidate
        embedded = _embedded_forge_root(candidate)
        if embedded is not None:
            return embedded
    raise FileNotFoundError(
        "Could not find a Forge project root. Run this inside a Forge workspace containing "
        "`system.yaml` and `runtime.yaml`, run it from a repository with `forge/`, or pass `--project-dir`."
    )
