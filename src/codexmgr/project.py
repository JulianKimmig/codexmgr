"""Project-level codexmgr orchestration commands."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agents_file import render_managed_agents_md
from .agentsmd import resolve_locked_agents_md
from .errors import CommandError
from .mcp import resolve_overrides
from .mcp_apply import apply_mcp_overrides, mcp_lock_data
from .paths import (
    agents_md_path,
    codex_config_path,
    config_path,
    lock_path,
    project_codex_dir,
)
from .project_config import load_required_project_config
from .renderer import render_agents_markdown
from .skills import resolve_codex_skill_entries
from .toml_io import dump_toml, ensure_toml_table, load_optional_toml_file


@dataclass(frozen=True)
class GeneratedFile:
    """Expected content for one codexmgr-managed generated file.

    Attributes:
        path: Filesystem path to the generated file.
        content: Expected UTF-8 text content for the generated file.
    """

    path: Path
    content: str


def setup_project(cwd: Path) -> Path:
    """Create the project .codex directory and source config file.

    Args:
        cwd: Project directory to initialize.

    Returns:
        The created or existing .codex directory path. Existing source config
        content is preserved.
    """
    codex_dir = project_codex_dir(cwd)
    codex_dir.mkdir(parents=True, exist_ok=True)
    source_config = config_path(cwd)
    if not source_config.exists():
        source_config.write_text("", encoding="utf-8")
    return codex_dir


def apply_project_config(cwd: Path, codex_home: Path, codexmgr_home: Path) -> None:
    """Apply project codexmgr configuration to generated Codex files.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named AGENTS.md sources.
    """
    for generated_file in build_project_files(cwd, codex_home, codexmgr_home):
        generated_file.path.write_text(generated_file.content, encoding="utf-8")


def build_project_files(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[GeneratedFile]:
    """Build expected generated file contents from project configuration.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named AGENTS.md sources.

    Returns:
        Expected generated files with their complete text content.
    """
    config = load_required_project_config(cwd)
    previous_lock = load_optional_toml_file(lock_path(cwd))
    locked_agents_md = resolve_locked_agents_md(config, cwd, codexmgr_home)
    skill_entries = resolve_codex_skill_entries(config, cwd, codex_home)
    mcp_overrides = resolve_overrides(config, strict=True)
    codex_config = _codex_config(
        cwd,
        config,
        skill_entries,
        mcp_overrides,
        previous_lock,
    )
    lock_data = _lock_data(config, locked_agents_md, skill_entries, mcp_overrides)
    return _generated_files(cwd, config, locked_agents_md, lock_data, codex_config)


def _generated_files(
    cwd: Path,
    config: dict[str, Any],
    locked_agents_md: dict[str, Any],
    lock_data: dict[str, Any],
    codex_config: dict[str, Any],
) -> list[GeneratedFile]:
    """Convert resolved project data into expected generated files.

    Args:
        cwd: Project directory whose generated files are being built.
        config: Parsed project codexmgr configuration.
        locked_agents_md: Resolved AGENTS.md source data.
        lock_data: Lockfile data to write.
        codex_config: Generated Codex config data.

    Returns:
        Expected generated files in write order.
    """
    files: list[GeneratedFile] = []
    if lock_data:
        files.append(GeneratedFile(lock_path(cwd), dump_toml(lock_data)))
    if "agents_md" in config:
        current_agents_md = _read_existing_text(agents_md_path(cwd))
        rendered = render_agents_markdown(locked_agents_md)
        files.append(
            GeneratedFile(
                agents_md_path(cwd),
                render_managed_agents_md(current_agents_md, rendered),
            )
        )
    files.append(GeneratedFile(codex_config_path(cwd), dump_toml(codex_config)))
    return files


def _read_existing_text(path: Path) -> str:
    """Read existing file text or return an empty string when missing.

    Args:
        path: UTF-8 text file path to read.

    Returns:
        Existing file content, or an empty string.
    """
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _codex_config(
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
        Parsed .codex/config.toml data with generated sections applied. Empty
        source config produces an empty local Codex config document.
    """
    codex_config = load_optional_toml_file(codex_config_path(cwd))
    if "skills" in config:
        _set_skill_config(codex_config, skill_entries)
    if "mcp" in config:
        apply_mcp_overrides(codex_config, mcp_overrides, previous_lock)
    return codex_config


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


def _lock_data(
    config: dict[str, Any],
    locked_agents_md: dict[str, Any],
    skill_entries: list[dict[str, Any]],
    mcp_overrides: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build lockfile data for configured AGENTS.md, skills, and MCP overrides.

    Args:
        config: Parsed project codexmgr configuration.
        locked_agents_md: Resolved AGENTS.md source data.
        skill_entries: Resolved Codex skill configuration entries.
        mcp_overrides: Resolved MCP server overrides.

    Returns:
        Lockfile data to write, or an empty dictionary when nothing is configured.
    """
    lock_data: dict[str, Any] = {}
    if "agents_md" in config:
        lock_data["agents_md"] = locked_agents_md
    if "skills" in config:
        lock_data["skills"] = {"config": skill_entries}
    if "mcp" in config:
        lock_data["mcp"] = mcp_lock_data(mcp_overrides)
    return lock_data
