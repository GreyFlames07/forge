from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import tomllib

__all__ = ["__version__"]

pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
if pyproject.exists():
    __version__ = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
else:
    try:
        __version__ = version("ai-forge-cli")
    except PackageNotFoundError:
        __version__ = "0.0.0"
