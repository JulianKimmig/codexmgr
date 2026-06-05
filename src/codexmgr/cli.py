"""Command line parsing and dispatch for codexmgr."""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from .agentsmd import add_agentsmd, list_agentsmd_options, remove_agentsmd
from .codex import run_codex
from .errors import CommandError
from .navigation import add_cd_arguments, format_codexmgr_home_command
from .paths import global_codex_dir, global_codexmgr_dir
from .project import apply_project_config, setup_project
from .skills import disable_skill, enable_skill


def main(
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    codex_home: Path | None = None,
    codexmgr_home: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Run the codexmgr command line interface.

    Args:
        argv: Optional argument list without the executable name.
        cwd: Optional project directory used instead of the current directory.
        codex_home: Optional Codex home used instead of CODEX_HOME or ~/.codex.
        codexmgr_home: Optional codexmgr home used instead of CODEXMGR_HOME
            or ~/.codexmgr.
        stdout: Optional stream for normal command output.
        stderr: Optional stream for command errors.

    Returns:
        A process-style exit code where zero means success.
    """
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(raw_argv)
    project_dir = cwd if cwd is not None else Path.cwd()
    codex_dir = codex_home if codex_home is not None else global_codex_dir()
    codexmgr_dir = (
        codexmgr_home if codexmgr_home is not None else global_codexmgr_dir()
    )

    try:
        return _dispatch(args, project_dir, codex_dir, codexmgr_dir, out)
    except CommandError as exc:
        err.write(f"{exc}\n")
        return 1


def entrypoint() -> None:
    """Run the console-script entrypoint.

    Returns:
        None. The function raises SystemExit with the CLI exit code.
    """
    raise SystemExit(main())


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse raw command line arguments.

    Args:
        argv: Command line arguments without the executable name.

    Returns:
        Parsed argparse namespace for dispatch.
    """
    if argv[:1] == ["codex"]:
        return argparse.Namespace(command="codex", codex_args=argv[1:])
    return _build_parser().parse_args(argv)


def _build_parser() -> argparse.ArgumentParser:
    """Build the codexmgr argument parser.

    Returns:
        Configured top-level argparse parser.
    """
    parser = argparse.ArgumentParser(prog="codexmgr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Create a project .codex directory")
    subparsers.add_parser("apply", help="Apply the project Codex configuration")
    cd = subparsers.add_parser("cd", help="Print shell navigation for CODEXMGR_HOME")
    add_cd_arguments(cd)

    codex = subparsers.add_parser("codex", add_help=False, help="Run codex with project config")
    codex.add_argument("codex_args", nargs=argparse.REMAINDER)

    agentsmd = subparsers.add_parser("agentsmd", help="Manage AGENTS.md fragments")
    agentsmd_subparsers = agentsmd.add_subparsers(dest="agentsmd_command", required=True)

    add = agentsmd_subparsers.add_parser("add", help="Add an AGENTS.md template")
    _add_no_sync_argument(add)
    add.add_argument("reference", help="Template name or TOML file path")

    remove = agentsmd_subparsers.add_parser("remove", help="Remove an AGENTS.md template")
    _add_no_sync_argument(remove)
    remove.add_argument("source_id", help="Template source identifier")

    agentsmd_subparsers.add_parser("list", help="List available AGENTS.md templates")

    skill = subparsers.add_parser("skill", help="Manage project skill configuration")
    skill_subparsers = skill.add_subparsers(dest="skill_command", required=True)

    enable = skill_subparsers.add_parser("enable", help="Enable a skill")
    _add_no_sync_argument(enable)
    enable.add_argument("skill", help="Skill name or path")

    disable = skill_subparsers.add_parser("disable", help="Disable a skill")
    _add_no_sync_argument(disable)
    disable.add_argument("skill", help="Skill name or path")

    return parser


def _add_no_sync_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared sync opt-out flag to a mutating command.

    Args:
        parser: Subcommand parser that updates .codex/codexmgr.toml.

    Returns:
        None. The parser is mutated in place.
    """
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not run apply after updating codexmgr.toml",
    )


def _dispatch(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run the parsed command.

    Args:
        args: Parsed command line namespace.
        cwd: Project directory for project-local operations.
        codex_home: Global Codex home for resolving named skills.
        codexmgr_home: codexmgr home for resolving named AGENTS.md templates.
        stdout: Stream for command output.

    Returns:
        A process-style exit code where zero means success.
    """
    if args.command == "setup":
        codex_dir = setup_project(cwd)
        stdout.write(f"Created {codex_dir}\n")
        return 0

    if args.command == "apply":
        apply_project_config(cwd, codex_home, codexmgr_home)
        stdout.write("Applied project Codex configuration\n")
        return 0

    if args.command == "cd":
        stdout.write(
            f"{format_codexmgr_home_command(codexmgr_home, args.cd_action)}\n"
        )
        return 0

    if args.command == "codex":
        return run_codex(cwd, args.codex_args)

    if args.command == "agentsmd" and args.agentsmd_command == "list":
        options = list_agentsmd_options(codexmgr_home)
        if options:
            stdout.write("\n".join(options) + "\n")
        return 0

    if args.command == "agentsmd" and args.agentsmd_command == "add":
        source_id = add_agentsmd(args.reference, cwd, codexmgr_home)
        return _finish_config_change(
            f"Added {source_id}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    if args.command == "agentsmd" and args.agentsmd_command == "remove":
        source_id = remove_agentsmd(args.source_id, cwd)
        return _finish_config_change(
            f"Removed {source_id}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    if args.command == "skill" and args.skill_command == "enable":
        skill = enable_skill(args.skill, cwd)
        return _finish_config_change(
            f"Enabled {skill}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    if args.command == "skill" and args.skill_command == "disable":
        skill = disable_skill(args.skill, cwd)
        return _finish_config_change(
            f"Disabled {skill}",
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )

    raise CommandError(f"Unsupported command: {args.command}")


def _finish_config_change(
    message: str,
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a project config mutation unless opted out.

    Args:
        message: Command-specific success message to write after all work succeeds.
        no_sync: Whether the command should skip the automatic apply step.
        cwd: Project directory whose configuration changed.
        codex_home: Global Codex home for resolving named skills during apply.
        codexmgr_home: codexmgr home for resolving named AGENTS.md templates.
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
