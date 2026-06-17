"""Build generated project files and lock data."""

from pathlib import Path
from typing import Any

from .state import GeneratedFile
from ..agents.file import render_managed_agents_md
from ..agents.renderer import render_agents_markdown
from ..core.paths import agents_md_path, codex_config_path, lock_path
from ..core.toml_io import dump_toml, ensure_toml_table, load_optional_toml_file
from ..hooks.resolution import HookResolution, hook_lock_data, hooks_json_file
from ..hooks.sources import project_hooks_json_path
from ..mcp.apply import apply_mcp_overrides, mcp_lock_data
from ..skills.copies import copy_lock_entries
from ..skills.resolution import SkillResolution


def build_codex_config(
    cwd: Path,
    config: dict[str, Any],
    skill_entries: list[dict[str, Any]],
    mcp_overrides: dict[str, dict[str, Any]],
    previous_lock: dict[str, Any],
) -> dict[str, Any]:
    """Build generated project-local Codex config content.

    Args:
        cwd: Project directory whose .codex/config.toml should be updated.
        config: Parsed project codexmgr configuration.
        skill_entries: Resolved Codex skill configuration entries.
        mcp_overrides: Resolved MCP server overrides.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Parsed .codex/config.toml data with generated sections applied.
    """
    codex_config = load_optional_toml_file(codex_config_path(cwd))
    if "skills" in config:
        _set_skill_config(codex_config, skill_entries)
    if "mcp" in config:
        apply_mcp_overrides(codex_config, mcp_overrides, previous_lock)
    return codex_config


def build_generated_files(
    cwd: Path,
    config: dict[str, Any],
    locked_agents_md: dict[str, Any],
    hook_resolution: HookResolution,
    lock_data: dict[str, Any],
    codex_config: dict[str, Any],
) -> list[GeneratedFile]:
    """Convert resolved project data into expected generated files.

    Args:
        cwd: Project directory whose generated files are being built.
        config: Parsed project codexmgr configuration.
        locked_agents_md: Resolved AGENTS.md source data.
        hook_resolution: Resolved hook bundle state.
        lock_data: Lockfile data to write.
        codex_config: Generated Codex config data.

    Returns:
        Expected generated files in write order.
    """
    files: list[GeneratedFile] = []
    if lock_data:
        files.append(GeneratedFile(lock_path(cwd), dump_toml(lock_data)))
    if "agents_md" in config:
        files.append(_agents_md_file(cwd, locked_agents_md))
    hook_file = hooks_json_file(hook_resolution, cwd)
    if hook_file is not None:
        path, content = hook_file
        files.append(GeneratedFile(path, content))
    files.append(GeneratedFile(codex_config_path(cwd), dump_toml(codex_config)))
    return files


def build_lock_data(
    config: dict[str, Any],
    locked_agents_md: dict[str, Any],
    skill_resolution: SkillResolution,
    hook_resolution: HookResolution,
    mcp_overrides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build lockfile data for configured AGENTS.md, skills, hooks, and MCP.

    Args:
        config: Parsed project codexmgr configuration.
        locked_agents_md: Resolved AGENTS.md source data.
        skill_resolution: Resolved skill configuration and copy state.
        hook_resolution: Resolved hook configuration and copy state.
        mcp_overrides: Resolved MCP server overrides.

    Returns:
        Lockfile data to write, or an empty dictionary when nothing is configured.
    """
    lock_data: dict[str, Any] = {}
    if "agents_md" in config:
        lock_data["agents_md"] = locked_agents_md
    if "skills" in config:
        lock_data["skills"] = {"config": skill_resolution.entries}
        copy_entries = copy_lock_entries(skill_resolution.copies)
        if copy_entries:
            lock_data["skills"]["copies"] = copy_entries
    if "hooks" in config:
        lock_data["hooks"] = hook_lock_data(hook_resolution)
    if "mcp" in config:
        lock_data["mcp"] = mcp_lock_data(mcp_overrides)
    return lock_data


def obsolete_generated_files(cwd: Path, hook_resolution: HookResolution) -> list[Path]:
    """Return generated files that should be removed during apply.

    Args:
        cwd: Project directory.
        hook_resolution: Resolved hook state.

    Returns:
        Obsolete file paths.
    """
    if not hook_resolution.remove_hooks_json:
        return []
    return [project_hooks_json_path(cwd)]


def remove_file_target(target: Path) -> None:
    """Remove one obsolete generated file when it exists.

    Args:
        target: File path to remove.
    """
    if target.exists():
        target.unlink()


def _agents_md_file(cwd: Path, locked_agents_md: dict[str, Any]) -> GeneratedFile:
    """Build the generated AGENTS.md file.

    Args:
        cwd: Project directory.
        locked_agents_md: Resolved AGENTS.md source data.

    Returns:
        Expected AGENTS.md generated file.
    """
    current_agents_md = _read_existing_text(agents_md_path(cwd))
    rendered = render_agents_markdown(locked_agents_md)
    return GeneratedFile(
        agents_md_path(cwd),
        render_managed_agents_md(current_agents_md, rendered),
    )


def _read_existing_text(path: Path) -> str:
    """Read existing file text or return an empty string when missing.

    Args:
        path: UTF-8 text file path to read.

    Returns:
        Existing file content, or an empty string.
    """
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _set_skill_config(codex_config: dict[str, Any], entries: list[dict[str, Any]]) -> None:
    """Set generated skills.config entries in a local Codex config document.

    Args:
        codex_config: Mutable .codex/config.toml document.
        entries: Resolved skills.config entries.
    """
    skills = ensure_toml_table(
        codex_config,
        "skills",
        ".codex/config.toml [skills] must be a table",
    )
    skills["config"] = entries
