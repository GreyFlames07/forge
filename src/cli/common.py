from __future__ import annotations

from pathlib import Path


FORGE_DIRNAME = "forge"


def find_forge_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    if current.is_dir() and current.name == FORGE_DIRNAME and (current / "system.yaml").exists():
        return current
    for candidate in (current, *current.parents):
        forge_dir = candidate / FORGE_DIRNAME
        if forge_dir.is_dir() and (forge_dir / "system.yaml").exists():
            return forge_dir
    raise FileNotFoundError(
        "Could not find a Forge project from the current directory. "
        "Run this inside a project root containing `forge/system.yaml`, inside the `forge/` directory itself, "
        "or pass `--forge-dir /path/to/forge`."
    )


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(name: str) -> str:
    return (
        name.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")
    )
