from __future__ import annotations

import argparse

from cli import __version__
from cli.commands import (
    register_context,
    register_graph,
    register_init,
    register_list,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forge", description="Forge V2 schema runtime and workbench CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_init(subparsers)
    register_graph(subparsers)
    register_context(subparsers)
    register_list(subparsers)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1
