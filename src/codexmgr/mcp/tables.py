"""Table-level mutation helpers for MCP project overrides."""

from collections.abc import MutableMapping
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import ensure_toml_table, plain_toml_value


def ensure_server(
    config: MutableMapping[str, Any],
    server_id: str,
) -> MutableMapping[str, Any]:
    """Return or create one project MCP server override table.

    Args:
        config: Project config document.
        server_id: MCP server id.

    Returns:
        Mutable server override table.
    """
    mcp = ensure_toml_table(config, "mcp", "codexmgr.toml [mcp] must be a table")
    servers = ensure_toml_table(mcp, "servers", "codexmgr.toml [mcp.servers] must be a table")
    return ensure_toml_table(
        servers,
        server_id,
        f"codexmgr.toml mcp.servers.{server_id} must be a table",
    )


def set_enabled_value(table: MutableMapping[str, Any], enabled: bool) -> None:
    """Set the enabled field on an MCP server table.

    Args:
        table: Server override table to mutate.
        enabled: Desired enabled state.
    """
    table["enabled"] = enabled


def add_env_var_value(table: MutableMapping[str, Any], env_var: str) -> None:
    """Add an env var to an override table.

    Args:
        table: Server override table.
        env_var: Env var name.
    """
    values = env_var_values(table)
    if env_var not in values:
        values.append(env_var)
    table["env_vars"] = values


def remove_env_var_value(table: MutableMapping[str, Any], env_var: str) -> None:
    """Remove an env var from an override table.

    Args:
        table: Server override table.
        env_var: Env var name.
    """
    values = env_var_values(table)
    table["env_vars"] = [value for value in values if value != env_var]


def env_var_values(table: MutableMapping[str, Any]) -> list[str]:
    """Return env_vars as a mutable plain list.

    Args:
        table: Server override table.

    Returns:
        Existing env_vars values.
    """
    values = plain_toml_value(table.get("env_vars", []))
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise CommandError("mcp.servers env_vars must be a list of strings")
    return values


def env_headers(table: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Return or create the env_http_headers override table.

    Args:
        table: Server override table.

    Returns:
        Mutable env_http_headers table.
    """
    return ensure_toml_table(table, "env_http_headers", "env_http_headers must be a string map")
