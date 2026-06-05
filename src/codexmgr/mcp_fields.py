"""Validate and format project-local MCP override fields."""

import tomllib
from collections.abc import Mapping
from typing import Any

from .errors import CommandError
from .toml_io import plain_toml_value

APPROVAL_MODES = {"auto", "prompt", "approve"}
SAFE_FIELDS = {
    "enabled",
    "required",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "enabled_tools",
    "disabled_tools",
    "default_tools_approval_mode",
    "bearer_token_env_var",
    "env_vars",
    "env_http_headers",
}
SET_FIELD_NAMES = {
    "required",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "enabled_tools",
    "disabled_tools",
    "default_tools_approval_mode",
}


def validate_override(server_id: str, table: Mapping[str, Any], *, strict: bool) -> None:
    """Validate one server override table.

    Args:
        server_id: MCP server id.
        table: Server override table.
        strict: Whether unsupported fields should fail.
    """
    for field, value in table.items():
        if field not in SAFE_FIELDS:
            if strict:
                raise CommandError(f"Unsupported MCP override field: {server_id}.{field}")
            continue
        validate_field(server_id, field, value)


def validate_field(server_id: str, field: str, value: Any) -> None:
    """Validate one override field value.

    Args:
        server_id: MCP server id.
        field: Field name.
        value: Field value.
    """
    value = plain_toml_value(value)
    if field in {"enabled", "required"} and not isinstance(value, bool):
        raise CommandError(f"mcp.servers.{server_id}.{field} must be a boolean")
    if field in {"startup_timeout_sec", "tool_timeout_sec"}:
        if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
            raise CommandError(f"mcp.servers.{server_id}.{field} must be a positive number")
    if field in {"enabled_tools", "disabled_tools"}:
        require_string_list(server_id, field, value)
    if field == "default_tools_approval_mode" and value not in APPROVAL_MODES:
        raise CommandError(f"{field} must be one of auto, prompt, approve")
    if field == "bearer_token_env_var" and not isinstance(value, str):
        raise CommandError(f"mcp.servers.{server_id}.{field} must be a string")
    if field == "env_vars":
        require_string_list(server_id, field, value)
    if field == "env_http_headers" and not is_string_map(value):
        raise CommandError(f"mcp.servers.{server_id}.{field} must be a string map")


def require_string_list(server_id: str, field: str, value: Any) -> None:
    """Require a list of strings.

    Args:
        server_id: MCP server id.
        field: Field name.
        value: Value to validate.
    """
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandError(f"mcp.servers.{server_id}.{field} must be a list of strings")


def is_string_map(value: Any) -> bool:
    """Return whether value is a string-to-string map.

    Args:
        value: Value to inspect.

    Returns:
        True when value is a string-to-string map.
    """
    value = plain_toml_value(value)
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, str)
        for key, item in value.items()
    )


def known_fields(table: Mapping[str, Any]) -> dict[str, Any]:
    """Return only fields supported by generated MCP overrides.

    Args:
        table: Server override table.

    Returns:
        Supported fields and values.
    """
    return {
        key: plain_toml_value(value)
        for key, value in table.items()
        if key in SAFE_FIELDS
    }


def unsupported_field_warnings(overrides: Mapping[str, Mapping[str, Any]]) -> list[str]:
    """Build validation warnings for unsupported project MCP fields.

    Args:
        overrides: Project MCP overrides.

    Returns:
        Warning lines.
    """
    warnings: list[str] = []
    for server_id, table in overrides.items():
        for field in table:
            if field not in SAFE_FIELDS:
                warnings.append(
                    f"WARN Unsupported MCP override field preserved nowhere: {server_id}.{field}"
                )
    return warnings


def parse_value(raw_value: str) -> Any:
    """Parse a TOML value literal.

    Args:
        raw_value: Raw TOML literal text.

    Returns:
        Parsed TOML value.
    """
    try:
        return tomllib.loads(f"value = {raw_value}")["value"]
    except tomllib.TOMLDecodeError as exc:
        raise CommandError(f"Invalid TOML value: {raw_value}") from exc
