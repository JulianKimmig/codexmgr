"""CLI helpers for reusable rule management commands."""

import argparse
from pathlib import Path
from typing import TextIO

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..project.apply import apply_project_config
from ..project.config import require_codex_dir
from ..rules.config import set_rule_state_in_config
from ..rules.listing import rule_list_lines


def run_rules_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed rules command.

    Args:
        args: Parsed rules command namespace.
        cwd: Project directory for project-local operations.
        codex_home: Codex home used by apply.
        codexmgr_home: Codexmgr home containing source rules.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    if args.rules_command == "list":
        _write_optional_lines(stdout, rule_list_lines(cwd, codexmgr_home))
        return 0
    enabled = args.rules_command == "enable"
    rules = _set_rule_many(args.rules, cwd, codexmgr_home, enabled=enabled)
    verb = "Enabled" if enabled else "Disabled"
    return _finish_config_change(
        [f"{verb} {rule}" for rule in rules],
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def _set_rule_many(
    rules: list[str],
    cwd: Path,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> list[str]:
    """Set multiple rule states with one config write.

    Args:
        rules: Rule refs to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: Codexmgr home containing source rules.
        enabled: Desired rule state.

    Returns:
        Canonical rule refs that were updated.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    updated = [
        set_rule_state_in_config(config, rule, codexmgr_home, enabled=enabled)
        for rule in rules
    ]
    write_toml_file(config_path(cwd), config)
    return updated


def _finish_config_change(
    messages: list[str],
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a rules mutation unless opted out.

    Args:
        messages: Command-specific success messages.
        no_sync: Whether to skip automatic apply.
        cwd: Project directory whose configuration changed.
        codex_home: Codex home for apply.
        codexmgr_home: Codexmgr home for apply.
        stdout: Stream for command output.

    Returns:
        Zero when mutation and optional apply succeed.
    """
    output = list(messages)
    if not no_sync:
        apply_project_config(cwd, codex_home, codexmgr_home)
        output.append("Applied project Codex configuration")
    stdout.write("\n".join(output) + "\n")
    return 0


def _write_optional_lines(stdout: TextIO, lines: list[str]) -> None:
    """Write lines only when present.

    Args:
        stdout: Stream for command output.
        lines: Lines to write.
    """
    if lines:
        stdout.write("\n".join(lines) + "\n")
