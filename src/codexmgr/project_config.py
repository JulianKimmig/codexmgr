"""Helpers for reading and updating project codexmgr configuration."""

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from .errors import CommandError
from .paths import config_path, project_codex_dir
from .toml_io import ensure_toml_table, load_toml_file


def require_codex_dir(cwd: Path) -> Path:
    """Return the project .codex directory or fail if it is missing.

    Args:
        cwd: Project directory to inspect.

    Returns:
        The project .codex directory path.
    """
    codex_dir = project_codex_dir(cwd)
    if not codex_dir.is_dir():
        raise CommandError(f"Project .codex directory not found: {codex_dir}")
    return codex_dir


def load_required_project_config(cwd: Path) -> MutableMapping[str, Any]:
    """Load .codex/codexmgr.toml or fail if it is missing.

    Args:
        cwd: Project directory whose codexmgr.toml should be loaded.

    Returns:
        Parsed project configuration.
    """
    require_codex_dir(cwd)
    path = config_path(cwd)
    if not path.is_file():
        raise CommandError(f"Project codexmgr.toml not found: {path}")
    return load_toml_file(path)


def agents_md_sources(config: Mapping[str, Any]) -> list[str]:
    """Return the configured AGENTS.md sources from project config.

    Args:
        config: Parsed .codex/codexmgr.toml content.

    Returns:
        The agents_md.src list.
    """
    agents_md = config.get("agents_md", {})
    if not isinstance(agents_md, Mapping):
        raise CommandError("codexmgr.toml [agents_md] must be a table")
    sources = agents_md.get("src", [])
    if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
        raise CommandError("codexmgr.toml agents_md.src must be a list of strings")
    return list(sources)


def set_agents_md_sources(config: MutableMapping[str, Any], sources: list[str]) -> None:
    """Set the AGENTS.md source list in project config.

    Args:
        config: Parsed .codex/codexmgr.toml content to mutate.
        sources: Source list to write as agents_md.src.
    """
    agents_md = ensure_toml_table(config, "agents_md", "codexmgr.toml [agents_md] must be a table")
    agents_md["src"] = sources
