"""Mutation helpers for existing user MCP servers."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

import tomlkit

from .errors import CommandError
from .mcp_model import SAFE_FIELDS, is_string_map, validate_env_vars, validate_field_value
from .mcp_user_config import mutate_server
from .user_config import parse_toml_value


def set_enabled(codex_home: Path, server_id: str, enabled: bool) -> str:
    """Set enabled on an existing MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        enabled: Desired enabled state.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: _set_enabled_field(server_id, table, enabled),
    )


def set_token_env(codex_home: Path, server_id: str, env_var: str) -> str:
    """Set bearer_token_env_var on an existing MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        env_var: Environment variable name to store.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: table.__setitem__("bearer_token_env_var", env_var),
    )


def add_env_var(codex_home: Path, server_id: str, env_var: str) -> str:
    """Add an env_vars string entry to an existing MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        env_var: Environment variable name to add.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: _add_env_var(server_id, table, env_var),
    )


def remove_env_var(codex_home: Path, server_id: str, env_var: str) -> str:
    """Remove string env_vars entries from an existing MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        env_var: Environment variable name to remove.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: _remove_env_var(server_id, table, env_var),
    )


def set_env_header(codex_home: Path, server_id: str, header: str, env_var: str) -> str:
    """Set an env_http_headers mapping entry on an existing MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        header: HTTP header name.
        env_var: Environment variable name for the header value.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: _env_headers(server_id, table).__setitem__(header, env_var),
    )


def unset_env_header(codex_home: Path, server_id: str, header: str) -> str:
    """Remove an env_http_headers mapping entry from an MCP server.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        header: HTTP header name to remove.

    Returns:
        The updated server id.
    """
    return mutate_server(
        codex_home,
        server_id,
        lambda table: _env_headers(server_id, table).pop(header, None),
    )


def set_field(codex_home: Path, server_id: str, field: str, raw_value: str) -> str:
    """Set one allowlisted MCP server field from a TOML literal.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.
        field: Allowlisted field name.
        raw_value: TOML literal text.

    Returns:
        The updated server id.
    """
    if field not in SAFE_FIELDS:
        raise CommandError(f"Unsupported MCP field for set-field: {field}")
    value = parse_toml_value(raw_value)
    validate_field_value(server_id, field, value)
    return mutate_server(
        codex_home,
        server_id,
        lambda table: table.__setitem__(field, value),
    )


def _set_enabled_field(server_id: str, table: MutableMapping[str, Any], enabled: bool) -> None:
    """Set enabled after checking the existing value shape.

    Args:
        server_id: MCP server identifier.
        table: Server table.
        enabled: Desired enabled state.
    """
    if "enabled" in table and not isinstance(table["enabled"], bool):
        raise CommandError(f"mcp_servers.{server_id}.enabled must be a boolean")
    table["enabled"] = enabled


def _add_env_var(server_id: str, table: MutableMapping[str, Any], env_var: str) -> None:
    """Add a string env var entry.

    Args:
        server_id: MCP server identifier.
        table: Server table.
        env_var: Env var name.
    """
    values = _env_vars(server_id, table)
    if env_var not in [item for item in values if isinstance(item, str)]:
        values.append(env_var)


def _remove_env_var(server_id: str, table: MutableMapping[str, Any], env_var: str) -> None:
    """Remove matching string env var entries.

    Args:
        server_id: MCP server identifier.
        table: Server table.
        env_var: Env var name.
    """
    values = _env_vars(server_id, table)
    updated = tomlkit.array()
    for item in values:
        if not (isinstance(item, str) and item == env_var):
            updated.append(item)
    table["env_vars"] = updated


def _env_vars(server_id: str, table: MutableMapping[str, Any]):
    """Return or create the env_vars array.

    Args:
        server_id: MCP server identifier.
        table: Server table.

    Returns:
        Mutable env_vars array.
    """
    if "env_vars" not in table:
        table["env_vars"] = tomlkit.array()
    values = table["env_vars"]
    validate_env_vars(server_id, values)
    return values


def _env_headers(server_id: str, table: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Return or create env_http_headers.

    Args:
        server_id: MCP server identifier.
        table: Server table.

    Returns:
        Mutable env_http_headers table.
    """
    if "env_http_headers" not in table:
        table["env_http_headers"] = tomlkit.table()
    values = table["env_http_headers"]
    if not is_string_map(values):
        raise CommandError(f"mcp_servers.{server_id}.env_http_headers must be a string map")
    return values
