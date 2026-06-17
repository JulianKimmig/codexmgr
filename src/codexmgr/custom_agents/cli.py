"""CLI dispatch helpers for custom-agent project configuration."""

import argparse
from pathlib import Path
from typing import TextIO

from ..core.errors import CommandError
from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..project.apply import apply_project_config
from ..project.config import require_codex_dir
from .config import set_agent_state_in_config
from .listing import agent_list_lines
from .sources import require_agent_source


def run_agents_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed custom-agent command.

    Args:
        args: Parsed custom-agent command namespace.
        cwd: Project directory for project-local operations.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home containing custom-agent sources.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    if args.agents_command == "list":
        _write_optional_lines(stdout, agent_list_lines(cwd, codexmgr_home))
        return 0
    enabled = args.agents_command == "enable"
    if args.agents_command not in {"enable", "disable"}:
        raise CommandError(f"Unsupported agents command: {args.agents_command}")
    agents = _set_agent_many(args.agents, cwd, codexmgr_home, enabled=enabled)
    verb = "Enabled" if enabled else "Disabled"
    return _finish_config_change(
        [f"{verb} {agent}" for agent in agents],
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def _set_agent_many(
    agents: list[str],
    cwd: Path,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> list[str]:
    """Set multiple custom-agent states with one config write.

    Args:
        agents: Custom-agent names to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home used to validate enabled agents.
        enabled: Desired custom-agent state.

    Returns:
        Custom-agent names that were requested.
    """
    if enabled:
        for agent in agents:
            require_agent_source(agent, codexmgr_home)
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    for agent in agents:
        set_agent_state_in_config(config, agent, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return list(agents)


def _finish_config_change(
    messages: list[str],
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a config mutation unless opted out.

    Args:
        messages: Command-specific success messages to write.
        no_sync: Whether the command should skip apply.
        cwd: Project directory whose configuration changed.
        codex_home: Global Codex home for apply.
        codexmgr_home: codexmgr home for reusable inputs.
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


def _write_optional_lines(stdout: TextIO, lines: list[str]) -> None:
    """Write lines only when the list is non-empty.

    Args:
        stdout: Stream for command output.
        lines: Lines to write.
    """
    if lines:
        stdout.write("\n".join(lines) + "\n")
