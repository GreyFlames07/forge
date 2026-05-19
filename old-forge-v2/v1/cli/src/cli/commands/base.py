"""
Command module contract.

Every module in `cli.commands` must expose:

  NAME: str
      The subcommand name. Used as `forge <NAME> ...` on the CLI.

  HELP: str
      One-line help text shown in `forge --help`.

  def register(sub: argparse._SubParsersAction) -> None:
      Add this command's subparser with all its arguments to the
      provided _SubParsersAction. MUST call
      `parser.set_defaults(handler=run)` on the created subparser so
      dispatch works without any if/elif chain in forge.main.

  def run(args: argparse.Namespace) -> int:
      Execute the command. Return an exit code:
        0 = success
        1 = usage error (unknown id, missing spec dir, etc.)
        2 = soft warning (e.g., bundle emitted but has unresolved refs)

Commands should reuse helpers from `cli.common` rather than reimplementing
spec-dir loading, id suggestion, or description formatting.
"""
