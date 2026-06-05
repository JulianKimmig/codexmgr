"""Read existing MCP servers from user Codex config."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Callable

from .errors import CommandError
from .mcp_model import McpServer, server_from_table, validate_server_fields, warning_lines
from .user_config import load_user_config, write_user_config


def servers(codex_home: Path) -> list[McpServer]:
    """Return configured MCP servers from user config.

    Args:
        codex_home: Codex home directory.

    Returns:
        Sorted MCP server summaries.
    """
    document = load_user_config(codex_home, required=False)
    mcp_servers = mcp_servers_table(document, required=False)
    if mcp_servers is None:
        return []
    return [
        server_from_table(server_id, table)
        for server_id, table in sorted(mcp_servers.items())
    ]


def server(codex_home: Path, server_id: str) -> McpServer:
    """Return one configured MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.

    Returns:
        MCP server summary.
    """
    document = load_user_config(codex_home, required=True)
    table = server_table(document, server_id)
    return server_from_table(server_id, table)


def validate(codex_home: Path, server_id: str | None = None) -> list[str]:
    """Validate MCP user config and return report lines.

    Args:
        codex_home: Codex home directory.
        server_id: Optional server id to validate.

    Returns:
        Validation report lines.
    """
    if server_id is None:
        all_servers = servers(codex_home)
    else:
        all_servers = [server(codex_home, server_id)]
    warnings: list[str] = []
    for item in all_servers:
        validate_server_fields(item.server_id, item.table)
        warnings.extend(warning_lines(item.server_id, item.table))
    if server_id is not None:
        return [f"Valid MCP server {server_id}", *warnings]
    count = len(all_servers)
    noun = "server" if count == 1 else "servers"
    return [f"Valid MCP config: {count} {noun}", *warnings]


def mutate_server(
    codex_home: Path,
    server_id: str,
    mutation: Callable[[MutableMapping[str, Any]], None],
) -> str:
    """Mutate one existing MCP server and write the user config.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        mutation: Callable that mutates the server table.

    Returns:
        The updated server id.
    """
    document = load_user_config(codex_home, required=True)
    table = server_table(document, server_id)
    validate_server_fields(server_id, table)
    mutation(table)
    write_user_config(codex_home, document)
    return server_id


def mcp_servers_table(document: MutableMapping[str, Any], *, required: bool):
    """Return the top-level mcp_servers table.

    Args:
        document: Parsed user config document.
        required: Whether the missing table is an error.

    Returns:
        The mcp_servers table or None.
    """
    if "mcp_servers" not in document:
        if required:
            raise CommandError("config.toml [mcp_servers] table not found")
        return None
    table = document["mcp_servers"]
    if not isinstance(table, MutableMapping):
        raise CommandError("config.toml [mcp_servers] must be a table")
    return table


def server_table(
    document: MutableMapping[str, Any],
    server_id: str,
) -> MutableMapping[str, Any]:
    """Return one existing MCP server table.

    Args:
        document: Parsed user config document.
        server_id: MCP server identifier.

    Returns:
        The existing server table.
    """
    mcp_servers = mcp_servers_table(document, required=True)
    if server_id not in mcp_servers:
        raise CommandError(f"MCP server not found: {server_id}")
    table = mcp_servers[server_id]
    if not isinstance(table, MutableMapping):
        raise CommandError(f"mcp_servers.{server_id} must be a table")
    return table
