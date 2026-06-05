"""Shell launching helpers for codexmgr home navigation."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import TextIO

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
        help="Open the codexmgr home in a file explorer",
    )
    output.add_argument(
        "--terminal",
        action="store_const",
        const=TERMINAL_ACTION,
        dest="cd_action",
        help="Open a new terminal in the codexmgr home",
    )


def run_codexmgr_home_action(
    codexmgr_home: Path,
    action: str,
    stdout: TextIO,
) -> int:
    """Run a codexmgr home navigation action.

    Args:
        codexmgr_home: codexmgr home directory targeted by the command.
        action: Navigation action to format. Supported values are ``cd``,
            ``path``, ``explorer``, and ``terminal``.
        stdout: Stream for path output when ``action`` is ``path``.

    Returns:
        The launched command exit code, or zero for path output.
    """
    if action == PATH_ACTION:
        stdout.write(f"{codexmgr_home}\n")
        return 0

    _require_codexmgr_home(codexmgr_home)
    if action == CD_ACTION:
        return _run_external_command(_current_shell_command(), codexmgr_home)
    if action == EXPLORER_ACTION:
        return _run_external_command(_file_explorer_command(codexmgr_home), None)
    if action == TERMINAL_ACTION:
        return _run_external_command(_terminal_command(codexmgr_home), None)
    raise CommandError(f"Unsupported codexmgr home action: {action}")


def _require_codexmgr_home(codexmgr_home: Path) -> None:
    """Require that the codexmgr home exists before launching into it.

    Args:
        codexmgr_home: codexmgr home directory to validate.

    Returns:
        None. A ``CommandError`` is raised when the path is not a directory.
    """
    if not codexmgr_home.is_dir():
        raise CommandError(f"codexmgr home not found: {codexmgr_home}")


def _current_shell_command() -> list[str]:
    """Build the current-terminal shell command.

    Returns:
        Command argv for launching the configured shell.
    """
    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC")
    if not shell:
        raise CommandError("Shell not configured: set SHELL or COMSPEC")
    return [shell]


def _file_explorer_command(codexmgr_home: Path) -> list[str]:
    """Build the platform file-explorer command.

    Args:
        codexmgr_home: codexmgr home directory to open.

    Returns:
        Command argv for opening the directory in a file explorer.
    """
    if sys.platform == "darwin":
        return ["open", str(codexmgr_home)]
    if sys.platform == "win32":
        return ["explorer", str(codexmgr_home)]
    if sys.platform.startswith("linux"):
        return ["xdg-open", str(codexmgr_home)]
    raise CommandError(f"File explorer command not configured for {sys.platform}")


def _terminal_command(codexmgr_home: Path) -> list[str]:
    """Build the platform new-terminal command.

    Args:
        codexmgr_home: codexmgr home directory to use as terminal cwd.

    Returns:
        Command argv for opening a new terminal in the directory.
    """
    if sys.platform == "darwin":
        return ["open", "-a", "Terminal", str(codexmgr_home)]
    if sys.platform == "win32":
        return ["wt", "-d", str(codexmgr_home)]
    if sys.platform.startswith("linux"):
        return ["x-terminal-emulator", "--working-directory", str(codexmgr_home)]
    raise CommandError(f"Terminal command not configured for {sys.platform}")


def _run_external_command(command: list[str], cwd: Path | None) -> int:
    """Run an external navigation command.

    Args:
        command: Command argv to run.
        cwd: Optional working directory for the launched process.

    Returns:
        The external command exit code.
    """
    try:
        return subprocess.run(command, cwd=cwd).returncode
    except FileNotFoundError as exc:
        raise CommandError(f"Command not found: {command[0]}") from exc
