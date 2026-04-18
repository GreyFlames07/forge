"""
Command registry.

To add a new command:
  1. Create `cli/commands/<name>.py` exposing NAME, HELP, register, run
     (see `base.py` for the contract, or copy any existing command as a
     starting point).
  2. Import it below and append to ALL_COMMANDS.

That's it — `forge.py` auto-discovers every command in ALL_COMMANDS,
builds its subparser, and wires dispatch via `args.handler`.
"""

from cli.commands import context as _context
from cli.commands import find as _find
from cli.commands import init as _init
from cli.commands import inspect as _inspect
from cli.commands import list_cmd as _list_cmd

ALL_COMMANDS = [
    _init,
    _context,
    _list_cmd,
    _inspect,
    _find,
]
