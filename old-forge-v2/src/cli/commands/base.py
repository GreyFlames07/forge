from __future__ import annotations

from argparse import ArgumentParser, Namespace


CommandHandler = callable


def add_forge_dir_arg(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--forge-dir",
        help="Path to the forge directory. Defaults to auto-discovery upward from the current directory.",
    )


def resolve_arg_path(args: Namespace, attr: str) -> str | None:
    return getattr(args, attr, None)
