from pathlib import Path

import pytest

from cli import index as index_mod


EXAMPLE_DIR = Path(__file__).resolve().parent.parent / "src" / "example"


@pytest.fixture(scope="session")
def example_dir() -> Path:
    return EXAMPLE_DIR


@pytest.fixture(scope="session")
def idx(example_dir: Path):
    return index_mod.load(example_dir)
