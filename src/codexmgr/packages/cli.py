"""CLI dispatch helpers for packaged codexmgr configurations."""

import argparse
from pathlib import Path
from typing import TextIO

from ..core.errors import CommandError
from ..project.apply import apply_project_config
from .listing import package_list_lines
from .mutation import disable_packages, enable_packages


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
        names = enable_packages(args.packages, cwd, codexmgr_home, args.profiles)
        return _finish_package_change(
            _package_messages("Enabled", names, args.profiles),
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    if args.package_command == "disable":
        names = disable_packages(args.packages, cwd, codexmgr_home, args.profiles)
        return _finish_package_change(
            _package_messages("Disabled", names, args.profiles),
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    raise CommandError(f"Unsupported package command: {args.package_command}")


def _finish_package_change(
    messages: list[str],
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a package mutation unless opted out.

    Args:
        messages: Command-specific success messages to write after all work
            succeeds.
        no_sync: Whether the command should skip the automatic apply step.
        cwd: Project directory whose configuration changed.
        codex_home: Global Codex home for resolving named skills during apply.
        codexmgr_home: codexmgr home for resolving named reusable inputs.
        stdout: Stream for command output.

    Returns:
        Zero when the mutation and optional apply step succeed.
    """
    output = list(messages)
    if not no_sync:
        apply_project_config(cwd, codex_home, codexmgr_home)
        output.append("Applied project Codex configuration")
    stdout.write("\n".join(output) + "\n")
    return 0


def _package_messages(
    verb: str,
    names: list[str],
    profiles: list[str],
) -> list[str]:
    """Build user-facing package mutation messages.

    Args:
        verb: Leading mutation verb, such as ``Enabled`` or ``Disabled``.
        names: Mutated package names.
        profiles: Selected package profiles.

    Returns:
        One message per package.
    """
    suffix = f" (profiles: {', '.join(profiles)})" if profiles else ""
    return [f"{verb} package {name}{suffix}" for name in names]
