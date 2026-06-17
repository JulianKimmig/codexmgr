"""CLI helpers for project configuration mutation commands."""

import argparse
from pathlib import Path
from typing import TextIO

from ..core.errors import CommandError
from ..core.paths import config_path, resolve_template
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..hooks.config import set_hook_state_in_config
from ..hooks.listing import hook_list_lines
from ..hooks.sources import require_hook_source
from ..project.apply import apply_project_config
from ..project.config import agents_md_sources, require_codex_dir, set_agents_md_sources
from ..skills.config import set_skill_state_in_config
from ..skills.listing import skill_list_lines


def run_agentsmd_mutation(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed AGENTS.md add or remove command.

    Args:
        args: Parsed agentsmd command namespace.
        cwd: Project directory for project-local operations.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home containing AGENTS.md templates.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    if args.agentsmd_command == "add":
        references = _add_agentsmd_many(args.references, cwd, codexmgr_home)
        return _finish_config_change(
            [f"Added {reference}" for reference in references],
            args.no_sync,
            cwd,
            codex_home,
            codexmgr_home,
            stdout,
        )
    sources = _remove_agentsmd_many(args.source_ids, cwd)
    return _finish_config_change(
        [f"Removed {source}" for source in sources],
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def run_skill_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed skill command.

    Args:
        args: Parsed skill command namespace.
        cwd: Project directory for project-local operations.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home used by apply.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    if args.skill_command == "list":
        _write_optional_lines(stdout, skill_list_lines(cwd, codex_home, codexmgr_home))
        return 0
    enabled = args.skill_command == "enable"
    skills = _set_skill_many(args.skills, cwd, enabled=enabled)
    verb = "Enabled" if enabled else "Disabled"
    return _finish_config_change(
        [f"{verb} {skill}" for skill in skills],
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def run_hooks_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed hooks command.

    Args:
        args: Parsed hooks command namespace.
        cwd: Project directory for project-local operations.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home containing hook bundles.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    if args.hooks_command == "list":
        _write_optional_lines(stdout, hook_list_lines(cwd, codexmgr_home))
        return 0
    enabled = args.hooks_command == "enable"
    hooks = _set_hook_many(args.hooks, cwd, codexmgr_home, enabled=enabled)
    verb = "Enabled" if enabled else "Disabled"
    return _finish_config_change(
        [f"{verb} {hook}" for hook in hooks],
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def _add_agentsmd_many(
    references: list[str],
    cwd: Path,
    codexmgr_home: Path,
) -> list[str]:
    """Add multiple AGENTS.md source references with one config write.

    Args:
        references: Template names or TOML file paths to add.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home used to validate named templates.

    Returns:
        References that were requested.
    """
    require_codex_dir(cwd)
    for reference in references:
        resolve_template(reference, cwd, codexmgr_home)
    config = load_optional_toml_file(config_path(cwd))
    sources = agents_md_sources(config)
    for reference in references:
        if reference not in sources:
            sources.append(reference)
    set_agents_md_sources(config, sources)
    write_toml_file(config_path(cwd), config)
    return list(references)


def _remove_agentsmd_many(source_ids: list[str], cwd: Path) -> list[str]:
    """Remove multiple AGENTS.md source references with one config write.

    Args:
        source_ids: Source identifiers or references to remove.
        cwd: Project directory whose codexmgr.toml should be updated.

    Returns:
        Source identifiers that were removed.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    sources = agents_md_sources(config)
    missing = [source_id for source_id in source_ids if source_id not in sources]
    if missing:
        raise CommandError(f"Source not found in codexmgr.toml: {missing[0]}")
    removed = set(source_ids)
    set_agents_md_sources(config, [source for source in sources if source not in removed])
    write_toml_file(config_path(cwd), config)
    return list(source_ids)


def _set_skill_many(skills: list[str], cwd: Path, *, enabled: bool) -> list[str]:
    """Set multiple skill states with one config write.

    Args:
        skills: Skill names or paths to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        enabled: Desired skill state.

    Returns:
        Skills that were requested.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    for skill in skills:
        set_skill_state_in_config(config, skill, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return list(skills)


def _set_hook_many(
    hooks: list[str],
    cwd: Path,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> list[str]:
    """Set multiple hook states with one config write.

    Args:
        hooks: Hook bundle names to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home used to validate enabled bundles.
        enabled: Desired hook state.

    Returns:
        Hook names that were requested.
    """
    if enabled:
        for hook in hooks:
            require_hook_source(hook, codexmgr_home)
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    for hook in hooks:
        set_hook_state_in_config(config, hook, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return list(hooks)


def _finish_config_change(
    messages: list[str],
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply generated files after a project config mutation unless opted out.

    Args:
        messages: Command-specific success messages to write after all work
            succeeds.
        no_sync: Whether the command should skip the automatic apply step.
        cwd: Project directory whose configuration changed.
        codex_home: Global Codex home for resolving named skills during apply.
        codexmgr_home: codexmgr home for resolving reusable inputs.
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
