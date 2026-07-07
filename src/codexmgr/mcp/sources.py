"""Resolve reusable MCP server source files from CODEXMGR_HOME."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file, plain_toml_value


@dataclass(frozen=True)
class McpSource:
    """One reusable MCP source file.

    Attributes:
        name: Bare source name from the file stem.
        source_file: Absolute path to the source TOML file.
        servers: Codex-shaped MCP server tables keyed by server id.
    """

    name: str
    source_file: Path
    servers: dict[str, dict[str, Any]]


def available_mcp_source_names(codexmgr_home: Path) -> list[str]:
    """List reusable MCP source names available under CODEXMGR_HOME.

    Args:
        codexmgr_home: Codexmgr home directory.

    Returns:
        Sorted source names with a TOML file.
    """
    root = mcp_sources_dir(codexmgr_home)
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.iterdir() if _is_mcp_source_file(path))


def resolve_mcp_source(name: str, codexmgr_home: Path) -> McpSource | None:
    """Resolve one reusable MCP source by bare name.

    Args:
        name: MCP source name from project configuration.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Resolved source, or None when the file is absent or the name is invalid.
    """
    if not is_bare_mcp_source_name(name):
        return None
    path = mcp_source_file(codexmgr_home, name)
    if not path.is_file():
        return None
    return load_mcp_source(name, path)


def require_mcp_source(name: str, codexmgr_home: Path) -> McpSource:
    """Resolve one reusable MCP source or raise a user-facing error.

    Args:
        name: MCP source name from the CLI or project configuration.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Resolved MCP source.
    """
    if not is_bare_mcp_source_name(name):
        raise CommandError(f"MCP source name must be a bare name: {name}")
    source = resolve_mcp_source(name, codexmgr_home)
    if source is None:
        raise CommandError(f"MCP source not found: {mcp_source_file(codexmgr_home, name)}")
    return source


def load_mcp_sources(names: list[str], codexmgr_home: Path) -> list[McpSource]:
    """Load enabled MCP sources and reject duplicate server ids.

    Args:
        names: MCP source names to load.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Loaded sources in input order.
    """
    sources = [require_mcp_source(name, codexmgr_home) for name in names]
    _validate_unique_server_ids(sources)
    return sources


def load_mcp_source(name: str, path: Path) -> McpSource:
    """Load and validate one reusable MCP source file.

    Args:
        name: Source name from the file stem.
        path: TOML file to load.

    Returns:
        Parsed MCP source.
    """
    data = load_toml_file(path)
    raw_servers = data.get("mcp_servers")
    if not isinstance(raw_servers, Mapping):
        raise CommandError(f"MCP source {path} must contain an [mcp_servers] table")
    unsupported = sorted(key for key in data if key != "mcp_servers")
    if unsupported:
        raise CommandError(f"MCP source {path} has unsupported top-level key: {unsupported[0]}")
    if not raw_servers:
        raise CommandError(f"MCP source {path} must define at least one MCP server")
    servers: dict[str, dict[str, Any]] = {}
    for server_id, table in raw_servers.items():
        if not isinstance(server_id, str) or not server_id.strip():
            raise CommandError(f"MCP source {path} contains an empty server id")
        if not isinstance(table, Mapping):
            raise CommandError(f"MCP source {path} mcp_servers.{server_id} must be a table")
        servers[server_id] = plain_toml_value(table)
    return McpSource(name, path.resolve(), servers)


def mcp_source_file(codexmgr_home: Path, name: str) -> Path:
    """Return the expected file path for a named MCP source.

    Args:
        codexmgr_home: Codexmgr home directory.
        name: Bare MCP source name.

    Returns:
        Path to CODEXMGR_HOME/mcp/<name>.toml.
    """
    return mcp_sources_dir(codexmgr_home) / f"{name}.toml"


def mcp_sources_dir(codexmgr_home: Path) -> Path:
    """Return the reusable MCP source directory.

    Args:
        codexmgr_home: Codexmgr home directory.

    Returns:
        Path to CODEXMGR_HOME/mcp.
    """
    return codexmgr_home / "mcp"


def is_bare_mcp_source_name(name: str) -> bool:
    """Return whether a source reference is a bare name.

    Args:
        name: MCP source reference from config or CLI input.

    Returns:
        True when the reference has no path separators or TOML suffix.
    """
    raw = name.strip()
    return bool(raw) and "/" not in raw and "\\" not in raw and not raw.endswith(".toml")


def _validate_unique_server_ids(sources: list[McpSource]) -> None:
    """Reject duplicate server ids across source files.

    Args:
        sources: Loaded MCP sources to inspect.
    """
    owner_by_server: dict[str, str] = {}
    for source in sources:
        for server_id in source.servers:
            owner = owner_by_server.get(server_id)
            if owner is not None:
                raise CommandError(
                    f"Duplicate MCP server id {server_id} from sources {owner} and {source.name}"
                )
            owner_by_server[server_id] = source.name


def _is_mcp_source_file(path: Path) -> bool:
    """Return whether a path is a top-level MCP source file.

    Args:
        path: Candidate source path.

    Returns:
        True when the path is a TOML file.
    """
    return path.is_file() and path.suffix == ".toml"
