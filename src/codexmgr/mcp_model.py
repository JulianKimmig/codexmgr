"""MCP server model and validation helpers."""

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from .errors import CommandError

APPROVAL_MODES = {"auto", "prompt", "approve"}
SAFE_FIELDS = {
    "required",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "enabled_tools",
    "disabled_tools",
    "default_tools_approval_mode",
}


@dataclass(frozen=True)
class McpServer:
    """Display-ready MCP server data.

    Attributes:
        server_id: MCP server identifier.
        table: Raw TOML table for the server.
        transport: Server transport summary.
        enabled: Effective enabled state.
        enabled_is_explicit: Whether the config has an enabled field.
    """

    server_id: str
    table: MutableMapping[str, Any]
    transport: str
    enabled: bool
    enabled_is_explicit: bool


def server_from_table(server_id: str, table: Any) -> McpServer:
    """Build display data for one MCP server table.

    Args:
        server_id: MCP server identifier.
        table: Raw server table.

    Returns:
        MCP server summary.
    """
    if not isinstance(table, MutableMapping):
        raise CommandError(f"mcp_servers.{server_id} must be a table")
    validate_server_fields(server_id, table)
    return McpServer(
        server_id=server_id,
        table=table,
        transport=transport(server_id, table),
        enabled=bool(table.get("enabled", True)),
        enabled_is_explicit="enabled" in table,
    )


def transport(server_id: str, table: MutableMapping[str, Any]) -> str:
    """Return the MCP transport for a server table.

    Args:
        server_id: MCP server identifier.
        table: Server table.

    Returns:
        Transport name.
    """
    has_command = "command" in table
    has_url = "url" in table
    if has_command == has_url:
        raise CommandError(f"mcp_servers.{server_id} must set exactly one of command or url")
    return "stdio" if has_command else "http"


def validate_server_fields(server_id: str, table: MutableMapping[str, Any]) -> None:
    """Validate MCP fields used by this feature.

    Args:
        server_id: MCP server identifier.
        table: Server table.
    """
    transport(server_id, table)
    if "enabled" in table and not isinstance(table["enabled"], bool):
        raise CommandError(f"mcp_servers.{server_id}.enabled must be a boolean")
    for field in ("enabled_tools", "disabled_tools"):
        if field in table:
            require_string_list(server_id, field, table[field])
    if "env_vars" in table:
        validate_env_vars(server_id, table["env_vars"])
    for field in ("env", "http_headers", "env_http_headers"):
        if field in table and not is_string_map(table[field]):
            raise CommandError(f"mcp_servers.{server_id}.{field} must be a string map")
    if "default_tools_approval_mode" in table:
        validate_approval_mode(
            "default_tools_approval_mode",
            table["default_tools_approval_mode"],
        )


def validate_field_value(server_id: str, field: str, value: Any) -> None:
    """Validate one set-field value.

    Args:
        server_id: MCP server identifier.
        field: Field name.
        value: Parsed TOML value.
    """
    if field == "required" and not isinstance(value, bool):
        raise CommandError("required must be a boolean")
    if field in {"startup_timeout_sec", "tool_timeout_sec"}:
        if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
            raise CommandError(f"{field} must be a positive number")
    if field in {"enabled_tools", "disabled_tools"}:
        require_string_list(server_id, field, value)
    if field == "default_tools_approval_mode":
        validate_approval_mode(field, value)


def validate_env_vars(server_id: str, values: Any) -> None:
    """Validate an env_vars array.

    Args:
        server_id: MCP server identifier.
        values: env_vars value.
    """
    if not isinstance(values, list):
        raise CommandError(f"mcp_servers.{server_id}.env_vars must be a list")
    for item in values:
        if isinstance(item, str):
            continue
        if not isinstance(item, MutableMapping):
            raise CommandError(f"mcp_servers.{server_id}.env_vars entries must be strings or tables")
        if not isinstance(item.get("name"), str):
            raise CommandError(f"mcp_servers.{server_id}.env_vars table entries need a string name")
        if "source" in item and item["source"] not in {"local", "remote"}:
            raise CommandError(f"mcp_servers.{server_id}.env_vars source must be local or remote")


def require_string_list(server_id: str, field: str, value: Any) -> None:
    """Require a value to be a list of strings.

    Args:
        server_id: MCP server identifier.
        field: Field name.
        value: Value to validate.
    """
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandError(f"mcp_servers.{server_id}.{field} must be a list of strings")


def is_string_map(value: Any) -> bool:
    """Return whether a value is a string-to-string mapping.

    Args:
        value: Value to validate.

    Returns:
        True for string-to-string mappings.
    """
    return isinstance(value, MutableMapping) and all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    )


def validate_approval_mode(field: str, value: Any) -> None:
    """Validate an MCP approval mode.

    Args:
        field: Field name.
        value: Field value.
    """
    if value not in APPROVAL_MODES:
        raise CommandError(f"{field} must be one of auto, prompt, approve")


def warning_lines(server_id: str, table: MutableMapping[str, Any]) -> list[str]:
    """Build deterministic warning lines for a server.

    Args:
        server_id: MCP server identifier.
        table: Server table.

    Returns:
        Warning lines without raw secret values.
    """
    warnings: list[str] = []
    if "env" in table and isinstance(table["env"], MutableMapping) and table["env"]:
        warnings.append(
            f"WARN Raw env values configured for {server_id}: "
            f"{', '.join(str(key) for key in table['env'])}"
        )
    if (
        "http_headers" in table
        and isinstance(table["http_headers"], MutableMapping)
        and table["http_headers"]
    ):
        warnings.append(
            f"WARN Static HTTP headers configured for {server_id}: "
            f"{', '.join(str(key) for key in table['http_headers'])}"
        )
    return warnings
