"""Shell command formatting for codexmgr home navigation."""

import argparse
from pathlib import Path
from shlex import quote

from .errors import CommandError

CD_ACTION = "cd"
EXPLORER_ACTION = "explorer"
PATH_ACTION = "path"
TERMINAL_ACTION = "terminal"


def add_cd_arguments(parser: argparse.ArgumentParser) -> None:
    """Add mutually exclusive codexmgr home navigation output options.

    Args:
        parser: ``cd`` subcommand parser to configure.

    Returns:
        None. The parser is mutated in place.
    """
    output = parser.add_mutually_exclusive_group()
    parser.set_defaults(cd_action=CD_ACTION)
    output.add_argument(
        "--path",
        action="store_const",
        const=PATH_ACTION,
        dest="cd_action",
        help="Print only the codexmgr home path",
    )
    output.add_argument(
        "--explorer",
        action="store_const",
        const=EXPLORER_ACTION,
        dest="cd_action",
        help="Print shell code that opens the codexmgr home in a file explorer",
    )
    output.add_argument(
        "--terminal",
        action="store_const",
        const=TERMINAL_ACTION,
        dest="cd_action",
        help="Print shell code that opens a terminal in the codexmgr home",
    )


def format_codexmgr_home_command(codexmgr_home: Path, action: str) -> str:
    """Format a shell-facing command for a codexmgr home action.

    Args:
        codexmgr_home: codexmgr home directory targeted by the command.
        action: Navigation action to format. Supported values are ``cd``,
            ``path``, ``explorer``, and ``terminal``.

    Returns:
        Shell-facing text for the requested action. The ``cd`` action is meant
        to be evaluated by the caller shell so it can affect the current
        terminal.
    """
    if action == CD_ACTION:
        return f"cd {_quote_home(codexmgr_home)}"
    if action == PATH_ACTION:
        return str(codexmgr_home)
    if action == EXPLORER_ACTION:
        return f"xdg-open {_quote_home(codexmgr_home)}"
    if action == TERMINAL_ACTION:
        return f"x-terminal-emulator --working-directory {_quote_home(codexmgr_home)}"
    raise CommandError(f"Unsupported codexmgr home action: {action}")


def _quote_home(codexmgr_home: Path) -> str:
    """Quote a codexmgr home path for POSIX-compatible shells.

    Args:
        codexmgr_home: codexmgr home directory to quote.

    Returns:
        The directory path quoted for safe shell interpolation.
    """
    return quote(str(codexmgr_home))
