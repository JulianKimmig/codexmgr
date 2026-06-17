"""CLI dispatch helpers for packaged codexmgr configurations."""

import argparse
from pathlib import Path
from typing import TextIO

from ..core.errors import CommandError
from ..project.apply import apply_project_config
from .listing import package_list_lines
from .mutation import disable_package, enable_package


def run_package_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run one parsed package subcommand.

    Args:
        args: Parsed argparse namespace for a package command.
        cwd: Project directory for project-local operations.
        codex_home: Global Codex home used by apply.
        codexmgr_home: codexmgr home containing package sources.
        stdout: Stream for normal command output.

    Returns:
        A process-style exit code where zero means success.
    """
    if args.package_command == "list":
        lines = package_list_lines(codexmgr_home)
        if lines:
            stdout.write("\n".join(lines) + "\n")
        return 0

    if args.package_command == "enable":
        name = enable_package(args.package, cwd, codexmgr_home)
        return _finish_package_change(
            f"Enabled package {name}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    if args.package_command == "disable":
        name = disable_package(args.package, cwd, codexmgr_home)
        return _finish_package_change(
            f"Disabled package {name}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    raise CommandError(f"Unsupported package command: {args.package_command}")


def _finish_package_change(
    message: str,
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a package mutation unless opted out.

    Args:
        message: Command-specific success message to write after all work succeeds.
        no_sync: Whether the command should skip the automatic apply step.
        cwd: Project directory whose configuration changed.
        codex_home: Global Codex home for resolving named skills during apply.
        codexmgr_home: codexmgr home for resolving named reusable inputs.
        stdout: Stream for command output.

    Returns:
        Zero when the mutation and optional apply step succeed.
    """
    messages = [message]
    if not no_sync:
        apply_project_config(cwd, codex_home, codexmgr_home)
        messages.append("Applied project Codex configuration")
    stdout.write("\n".join(messages) + "\n")
    return 0
