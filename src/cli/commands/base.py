from __future__ import annotations

from argparse import ArgumentParser


def add_project_dir_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--project-dir",
        "--forge-dir",
        dest="project_dir",
        help="Path to the Forge project root. Defaults to auto-discovery upward from the current directory.",
    )
