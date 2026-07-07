"""Resolve project MCP sources and server overlays into generated config."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file
from ..project.config import require_codex_dir
from .config import resolve_overrides
from .project import mcp_source_names
from .sources import load_mcp_sources


@dataclass(frozen=True)
class McpResolution:
    """Resolved MCP configuration for one project.

    Attributes:
        enabled_sources: Reusable MCP source names enabled by the project.
        servers: Generated Codex MCP server tables keyed by server id.
    """

    enabled_sources: list[str]
    servers: dict[str, dict[str, Any]]


def empty_mcp_resolution() -> McpResolution:
    """Return an empty MCP resolution.

    Returns:
        A resolution with no enabled sources or generated servers.
    """
    return McpResolution([], {})


def resolve_project_mcp(
    project_config: Mapping[str, Any],
    codexmgr_home: Path,
) -> McpResolution:
    """Resolve reusable MCP sources and project server overlays.

    Args:
        project_config: Parsed project codexmgr configuration.
        codexmgr_home: Codexmgr home directory containing MCP source files.

    Returns:
        Resolved MCP server tables.
    """
    enabled_sources = mcp_source_names(project_config)
    servers = _source_servers(enabled_sources, codexmgr_home)
    for server_id, fields in resolve_overrides(project_config, strict=True).items():
        merged = dict(servers.get(server_id, {}))
        merged.update(fields)
        servers[server_id] = merged
    return McpResolution(enabled_sources, servers)


def validate_mcp_config(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Validate project MCP configuration and return report lines.

    Args:
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory containing MCP sources.

    Returns:
        Validation report lines.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    resolution = resolve_project_mcp(config, codexmgr_home)
    source_count = len(resolution.enabled_sources)
    server_count = len(resolution.servers)
    return [
        "Valid MCP config: "
        f"{source_count} {_noun(source_count, 'source')}, "
        f"{server_count} {_noun(server_count, 'server')}"
    ]


def _source_servers(
    enabled_sources: list[str],
    codexmgr_home: Path,
) -> dict[str, dict[str, Any]]:
    """Load generated server tables from reusable sources.

    Args:
        enabled_sources: Source names to load.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Generated server tables keyed by server id.
    """
    servers: dict[str, dict[str, Any]] = {}
    for source in load_mcp_sources(enabled_sources, codexmgr_home):
        for server_id, table in source.servers.items():
            servers[server_id] = dict(table)
    return servers


def _noun(count: int, singular: str) -> str:
    """Return a singular or plural display noun.

    Args:
        count: Number of items.
        singular: Singular noun form.

    Returns:
        Singular noun for one, plural otherwise.
    """
    return singular if count == 1 else f"{singular}s"
