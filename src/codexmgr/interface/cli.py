"""Command line parsing and dispatch for codexmgr."""

import argparse
import sys
from pathlib import Path
from typing import TextIO

from ..agents.manager import (
    init_agentsmd_template,
    list_agentsmd_options,
    show_agentsmd,
    validate_agentsmd,
)
from ..commands.codex import run_codex_command
from ..commands.config_mutations import (
    run_agentsmd_mutation,
    run_hooks_command,
    run_skill_command,
)
from ..commands.health import run_doctor, run_status
from ..commands.navigation import run_codexmgr_home_action
from ..core.errors import CommandError
from ..core.paths import global_codex_dir, global_codexmgr_dir
from ..custom_agents.cli import run_agents_command
from ..mcp.cli import run_mcp_command
from ..packages.cli import run_package_command
from ..project.apply import apply_project_config, setup_project
from ..project.sync import check_project_sync
from ..tui.cli import run_tui_command
from .parser import build_parser


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
    return build_parser().parse_args(argv)


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
        apply_project_config(cwd, codex_home, codexmgr_home)
        stdout.write(f"Created {codex_dir}\nApplied project Codex configuration\n")
        return 0

    if args.command == "apply":
        if args.check or args.diff:
            return check_project_sync(
                cwd,
                codex_home,
                codexmgr_home,
                stdout,
                show_diff=args.diff,
            )
        apply_project_config(cwd, codex_home, codexmgr_home)
        stdout.write("Applied project Codex configuration\n")
        return 0

    if args.command == "cd":
        return run_codexmgr_home_action(codexmgr_home, args.cd_action, stdout)

    if args.command == "codex":
        return run_codex_command(cwd, codex_home, codexmgr_home, args.codex_args)

    if args.command == "agentsmd" and args.agentsmd_command == "list":
        options = list_agentsmd_options(codexmgr_home)
        if options:
            stdout.write("\n".join(options) + "\n")
        return 0

    if args.command == "agentsmd" and args.agentsmd_command == "show":
        stdout.write(show_agentsmd(args.reference, cwd, codexmgr_home))
        return 0

    if args.command == "agentsmd" and args.agentsmd_command == "validate":
        source_id = validate_agentsmd(args.reference, cwd, codexmgr_home)
        stdout.write(f"Valid {source_id}\n")
        return 0

    if args.command == "agentsmd" and args.agentsmd_command == "add":
        return run_agentsmd_mutation(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "agentsmd" and args.agentsmd_command == "remove":
        return run_agentsmd_mutation(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "agents":
        return run_agents_command(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "skill":
        return run_skill_command(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "hooks":
        return run_hooks_command(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "package":
        return run_package_command(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "mcp":
        return run_mcp_command(args, cwd, codex_home, codexmgr_home, stdout)

    if args.command == "tui":
        return run_tui_command(args, cwd, codex_home, codexmgr_home)

    if args.command == "doctor":
        return run_doctor(cwd, codex_home, codexmgr_home, stdout)

    if args.command == "status":
        return run_status(cwd, codex_home, codexmgr_home, stdout)

    if args.command == "init-template" and args.init_template_command == "agentsmd":
        path = init_agentsmd_template(args.name, codexmgr_home)
        stdout.write(f"Created {path}\n")
        return 0

    raise CommandError(f"Unsupported command: {args.command}")
