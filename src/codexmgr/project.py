"""Project-level codexmgr orchestration commands."""

from pathlib import Path
from typing import Any

from .agentsmd import resolve_locked_agents_md, write_agents_md
from .paths import codex_config_path, lock_path, project_codex_dir
from .project_config import load_required_project_config
from .skills import build_codex_skill_config, resolve_codex_skill_entries
from .toml_io import write_toml_file


def setup_project(cwd: Path) -> Path:
    """Create the project .codex directory.

    Args:
        cwd: Project directory to initialize.

    Returns:
        The created or existing .codex directory path.
    """
    codex_dir = project_codex_dir(cwd)
    codex_dir.mkdir(parents=True, exist_ok=True)
    return codex_dir


def apply_project_config(cwd: Path, codex_home: Path) -> None:
    """Apply project codexmgr configuration to generated Codex files.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named sources.
    """
    config = load_required_project_config(cwd)
    locked_agents_md = resolve_locked_agents_md(config, cwd, codex_home)
    skill_entries = resolve_codex_skill_entries(config, cwd, codex_home)
    codex_config = build_codex_skill_config(skill_entries, cwd)
    lock_data = _lock_data(config, locked_agents_md, skill_entries)

    if lock_data:
        write_toml_file(lock_path(cwd), lock_data)
    if "agents_md" in config:
        write_agents_md(cwd, locked_agents_md)
    if codex_config is not None:
        write_toml_file(codex_config_path(cwd), codex_config)


def _lock_data(
    config: dict[str, Any],
    locked_agents_md: dict[str, Any],
    skill_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    lock_data: dict[str, Any] = {}
    if "agents_md" in config:
        lock_data["agents_md"] = locked_agents_md
    if skill_entries:
        lock_data["skills"] = {"config": skill_entries}
    return lock_data
