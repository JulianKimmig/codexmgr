import argparse
import sys
from pathlib import Path
from typing import TextIO

from .agentsmd import add_agentsmd, remove_agentsmd
from .codex import run_codex
from .errors import CommandError
from .paths import global_codex_dir
from .project import apply_project_config, setup_project
from .skills import disable_skill, enable_skill


def main(
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    codex_home: Path | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = _parse_args(raw_argv)
    project_dir = cwd if cwd is not None else Path.cwd()
    global_dir = codex_home if codex_home is not None else global_codex_dir()

    try:
        return _dispatch(args, project_dir, global_dir, out)
    except CommandError as exc:
        err.write(f"{exc}\n")
        return 1


def entrypoint() -> None:
    raise SystemExit(main())


def _parse_args(argv: list[str]) -> argparse.Namespace:
    if argv[:1] == ["codex"]:
        return argparse.Namespace(command="codex", codex_args=argv[1:])
    return _build_parser().parse_args(argv)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codexmgr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Create a project .codex directory")
    subparsers.add_parser("apply", help="Apply the project Codex configuration")

    codex = subparsers.add_parser("codex", add_help=False, help="Run codex with project config")
    codex.add_argument("codex_args", nargs=argparse.REMAINDER)

    agentsmd = subparsers.add_parser("agentsmd", help="Manage AGENTS.md fragments")
    agentsmd_subparsers = agentsmd.add_subparsers(dest="agentsmd_command", required=True)

    add = agentsmd_subparsers.add_parser("add", help="Add an AGENTS.md template")
    add.add_argument("reference", help="Template name or TOML file path")

    remove = agentsmd_subparsers.add_parser("remove", help="Remove an AGENTS.md template")
    remove.add_argument("source_id", help="Template source identifier")

    skill = subparsers.add_parser("skill", help="Manage project skill configuration")
    skill_subparsers = skill.add_subparsers(dest="skill_command", required=True)

    enable = skill_subparsers.add_parser("enable", help="Enable a skill")
    enable.add_argument("skill", help="Skill name or path")

    disable = skill_subparsers.add_parser("disable", help="Disable a skill")
    disable.add_argument("skill", help="Skill name or path")

    return parser


def _dispatch(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    stdout: TextIO,
) -> int:
    if args.command == "setup":
        codex_dir = setup_project(cwd)
        stdout.write(f"Created {codex_dir}\n")
        return 0

    if args.command == "apply":
        apply_project_config(cwd, codex_home)
        stdout.write("Applied project Codex configuration\n")
        return 0

    if args.command == "codex":
        return run_codex(cwd, args.codex_args)

    if args.command == "agentsmd" and args.agentsmd_command == "add":
        source_id = add_agentsmd(args.reference, cwd, codex_home)
        stdout.write(f"Added {source_id}\n")
        return 0

    if args.command == "agentsmd" and args.agentsmd_command == "remove":
        source_id = remove_agentsmd(args.source_id, cwd)
        stdout.write(f"Removed {source_id}\n")
        return 0

    if args.command == "skill" and args.skill_command == "enable":
        skill = enable_skill(args.skill, cwd)
        stdout.write(f"Enabled {skill}\n")
        return 0

    if args.command == "skill" and args.skill_command == "disable":
        skill = disable_skill(args.skill, cwd)
        stdout.write(f"Disabled {skill}\n")
        return 0

    raise CommandError(f"Unsupported command: {args.command}")
