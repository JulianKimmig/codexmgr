"""Project status and diagnostic checks for codexmgr."""

import os
from pathlib import Path
from typing import TextIO

from ..agents.manager import resolve_locked_agents_md
from ..core.errors import CommandError
from ..core.paths import project_codex_dir
from ..custom_agents.listing import configured_agent_lists, missing_enabled_agents
from ..project.config import agents_md_sources, load_required_project_config
from ..project.sync import generated_file_diffs
from ..hooks.listing import configured_hook_lists, missing_enabled_hooks
from ..rules.listing import configured_rule_lists, missing_enabled_rules
from ..skills.listing import configured_skill_lists, missing_enabled_skills


def run_status(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Write a compact status summary for the current project.

    Args:
        cwd: Project directory to inspect.
        codex_home: Global Codex home used to resolve skills.
        codexmgr_home: codexmgr home used to resolve snippets.
        stdout: Stream for status output.

    Returns:
        Zero when the summary was written.
    """
    config = load_required_project_config(cwd)
    enabled, disabled = configured_skill_lists(cwd)
    enabled_hooks, disabled_hooks = configured_hook_lists(cwd)
    enabled_agents, disabled_agents = configured_agent_lists(cwd)
    enabled_rules, disabled_rules = configured_rule_lists(cwd)
    diffs = generated_file_diffs(cwd, codex_home, codexmgr_home)
    lines = [
        f"Project: {cwd}",
        f"CODEX_HOME: {codex_home}",
        f"CODEXMGR_HOME: {codexmgr_home}",
        f"AGENTS.md snippets: {_format_values(agents_md_sources(config))}",
        f"Enabled skills: {_format_values(enabled)}",
        f"Disabled skills: {_format_values(disabled)}",
        f"Enabled hooks: {_format_values(enabled_hooks)}",
        f"Disabled hooks: {_format_values(disabled_hooks)}",
        f"Enabled agents: {_format_values(enabled_agents)}",
        f"Disabled agents: {_format_values(disabled_agents)}",
        f"Enabled rules: {_format_values(enabled_rules)}",
        f"Disabled rules: {_format_values(disabled_rules)}",
        f"Generated files: {_sync_state(diffs)}",
    ]
    lines.extend(f"  {diff.relative_path}" for diff in diffs)
    stdout.write("\n".join(lines) + "\n")
    return 0


def run_doctor(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run project diagnostics and write a health report.

    Args:
        cwd: Project directory to inspect.
        codex_home: Global Codex home used to resolve skills.
        codexmgr_home: codexmgr home used to resolve snippets.
        stdout: Stream for diagnostic output.

    Returns:
        Zero when no errors are found, one when at least one error is found.
    """
    report = _home_warnings(codex_home, codexmgr_home)
    if not project_codex_dir(cwd).is_dir():
        report.append(f"ERROR Project .codex directory not found: {project_codex_dir(cwd)}")
        stdout.write("\n".join(report) + "\n")
        return 1

    config = _load_config_for_doctor(cwd, report)
    if config is None:
        stdout.write("\n".join(report) + "\n")
        return 1

    _check_agents_sources(config, cwd, codexmgr_home, report)
    _check_missing_enabled_skills(cwd, codex_home, codexmgr_home, report)
    _check_missing_enabled_hooks(cwd, codexmgr_home, report)
    _check_missing_enabled_agents(cwd, codexmgr_home, report)
    _check_missing_enabled_rules(cwd, codexmgr_home, report)
    _check_generated_files(cwd, codex_home, codexmgr_home, report)

    has_errors = any(line.startswith("ERROR ") for line in report)
    if not has_errors:
        report.append("OK Project checks passed")
    stdout.write("\n".join(report) + "\n")
    return 1 if has_errors else 0


def _home_warnings(codex_home: Path, codexmgr_home: Path) -> list[str]:
    """Build warnings for unset home environment variables.

    Args:
        codex_home: Resolved Codex home path.
        codexmgr_home: Resolved codexmgr home path.

    Returns:
        Warning lines for unset environment variables.
    """
    warnings: list[str] = []
    if "CODEX_HOME" not in os.environ:
        warnings.append(f"WARN CODEX_HOME not set; using {codex_home}")
    if "CODEXMGR_HOME" not in os.environ:
        warnings.append(f"WARN CODEXMGR_HOME not set; using {codexmgr_home}")
    return warnings


def _load_config_for_doctor(cwd: Path, report: list[str]) -> dict | None:
    """Load project configuration for doctor checks.

    Args:
        cwd: Project directory whose config should be loaded.
        report: Mutable diagnostic report receiving any error.

    Returns:
        Parsed config, or None when loading failed.
    """
    try:
        return load_required_project_config(cwd)
    except CommandError as exc:
        report.append(f"ERROR {exc}")
        return None


def _check_agents_sources(
    config: dict,
    cwd: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that configured AGENTS.md sources resolve.

    Args:
        config: Parsed project config.
        cwd: Project directory used to resolve path snippets.
        codexmgr_home: codexmgr home used to resolve named snippets.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    try:
        resolve_locked_agents_md(config, cwd, codexmgr_home)
    except CommandError as exc:
        report.append(f"ERROR {exc}")


def _check_missing_enabled_skills(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that enabled skill references resolve.

    Args:
        cwd: Project directory whose configured skills should be checked.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named skills.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    for skill in missing_enabled_skills(cwd, codex_home, codexmgr_home):
        report.append(f"ERROR Missing enabled skill: {skill}")


def _check_missing_enabled_hooks(
    cwd: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that enabled hook bundle references resolve.

    Args:
        cwd: Project directory whose configured hooks should be checked.
        codexmgr_home: codexmgr home used to resolve named hook bundles.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    for hook in missing_enabled_hooks(cwd, codexmgr_home):
        report.append(f"ERROR Missing enabled hook: {hook}")


def _check_missing_enabled_agents(
    cwd: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that enabled custom-agent references resolve.

    Args:
        cwd: Project directory whose configured custom agents should be checked.
        codexmgr_home: codexmgr home used to resolve custom-agent sources.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    for agent in missing_enabled_agents(cwd, codexmgr_home):
        report.append(f"ERROR Missing enabled agent: {agent}")


def _check_missing_enabled_rules(
    cwd: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that enabled reusable rule references resolve.

    Args:
        cwd: Project directory whose configured rules should be checked.
        codexmgr_home: codexmgr home used to resolve reusable rules.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    for rule in missing_enabled_rules(cwd, codexmgr_home):
        report.append(f"ERROR Missing enabled rule: {rule}")


def _check_generated_files(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    report: list[str],
) -> None:
    """Check that generated files are in sync.

    Args:
        cwd: Project directory whose generated files should be checked.
        codex_home: Global Codex home used to resolve skills.
        codexmgr_home: codexmgr home used to resolve snippets.
        report: Mutable diagnostic report receiving any error.

    Returns:
        None.
    """
    try:
        for diff in generated_file_diffs(cwd, codex_home, codexmgr_home):
            report.append(f"ERROR Out of sync: {diff.relative_path}")
    except CommandError as exc:
        report.append(f"ERROR {exc}")


def _format_values(values: list[str]) -> str:
    """Format a list of configured values for compact status output.

    Args:
        values: Configured values to display.

    Returns:
        Comma-separated values, or ``none``.
    """
    return ", ".join(values) if values else "none"


def _sync_state(diffs: list[object]) -> str:
    """Return the display sync state for status output.

    Args:
        diffs: Generated-file differences.

    Returns:
        ``in sync`` when no diffs exist, otherwise ``out of sync``.
    """
    return "out of sync" if diffs else "in sync"
