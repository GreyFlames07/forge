"""
`forge` CLI entry point.

This module is deliberately thin: it collects registered command
modules, lets each build its own subparser, and dispatches via
`args.handler`. Adding a new command requires zero edits here — see
`cli.commands.__init__` for the registration point.
"""

from __future__ import annotations

import argparse
from importlib import metadata

from cli.commands import ALL_COMMANDS


def _version_string() -> str:
    """Return the installed forge-cli package version."""
    for dist_name in ("forge-ai-cli", "forge-cli"):
        try:
            return metadata.version(dist_name)
        except metadata.PackageNotFoundError:
            continue
    return "unknown"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forge",
        description=(
            "Context walker for the Forge L0-L5 spec system. "
            "Assembles everything an agent needs to implement an atom, "
            "module, journey, flow, or artifact into a single bundle."
        ),
        epilog=(
            "Examples:\n"
            "  forge context atm.pay.charge_card --spec-dir src/example\n"
            "  forge list --kind atom\n"
            "  forge inspect PAY\n\n"
            "Spec dir resolution: --spec-dir > $FORGE_SPEC_DIR > auto-discover."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"forge {_version_string()}",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    for cmd in ALL_COMMANDS:
        cmd.register(sub)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
