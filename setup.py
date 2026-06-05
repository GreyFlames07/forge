from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


ROOT = Path(__file__).resolve().parent
SYNC_SCRIPT = ROOT / "scripts" / "sync_package_resources.py"


def sync_package_resources() -> None:
    if not SYNC_SCRIPT.exists() or not (ROOT / "skills").exists():
        return
    subprocess.run([sys.executable, str(SYNC_SCRIPT)], check=True)


class build_py(_build_py):
    def run(self) -> None:
        sync_package_resources()
        super().run()


class sdist(_sdist):
    def run(self) -> None:
        sync_package_resources()
        super().run()


setup(cmdclass={"build_py": build_py, "sdist": sdist})
