"""Project-local MCP override configuration for codexmgr."""

from collections.abc import Callable, Mapping, MutableMapping
from pathlib import Path
from typing import Any

from .errors import CommandError
from .mcp_fields import (
    SET_FIELD_NAMES,
    parse_value,
    unsupported_field_warnings,
    validate_field,
    validate_override,
)
from .paths import config_path
from .project_config import require_codex_dir
from .toml_io import (
    ensure_toml_table,
    load_optional_toml_file,
    plain_toml_value,
    write_toml_file,
)

Mutation = Callable[[MutableMapping[str, Any]], None]


def configured_overrides(cwd: Path) -> dict[str, dict[str, Any]]:
    """Return configured MCP server overrides from project config.

    Args:
        cwd: Project directory.

    Returns:
        MCP overrides keyed by server id.
    """
    config = load_optional_toml_file(config_path(cwd))
    return resolve_overrides(config, strict=False)


def resolve_overrides(
    project_config: Mapping[str, Any],
    *,
    strict: bool,
) -> dict[str, dict[str, Any]]:
    """Extract MCP overrides from project config.

    Args:
        project_config: Project codexmgr configuration.
        strict: Whether unsupported fields should fail.

    Returns:
        MCP overrides keyed by server id.
    """
    mcp = project_config.get("mcp", {})
    if not isinstance(mcp, Mapping):
        raise CommandError("codexmgr.toml [mcp] must be a table")
    servers = mcp.get("servers", {})
    if not isinstance(servers, Mapping):
        raise CommandError("codexmgr.toml [mcp.servers] must be a table")
    for server_id, table in servers.items():
        if not isinstance(table, Mapping):
            raise CommandError(f"codexmgr.toml mcp.servers.{server_id} must be a table")
        validate_override(server_id, table, strict=strict)
    return {
        server_id: {key: plain_toml_value(value) for key, value in table.items()}
        for server_id, table in servers.items()
    }


def validate_overrides(cwd: Path) -> list[str]:
    """Validate project MCP overrides and return report lines.

    Args:
        cwd: Project directory.

    Returns:
        Validation report lines.
    """
    require_codex_dir(cwd)
    overrides = configured_overrides(cwd)
    warnings = unsupported_field_warnings(overrides)
    count = len(overrides)
    noun = "server override" if count == 1 else "server overrides"
    return [f"Valid MCP config: {count} {noun}", *warnings]


def set_enabled(cwd: Path, server_id: str, enabled: bool) -> str:
    """Set an MCP enabled override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        enabled: Desired enabled state.

    Returns:
        Updated server id.
    """
    return _mutate_server(cwd, server_id, lambda table: table.__setitem__("enabled", enabled))


def set_token_env(cwd: Path, server_id: str, env_var: str) -> str:
    """Set bearer_token_env_var in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        env_var: Environment variable name.

    Returns:
        Updated server id.
    """
    return _mutate_server(
        cwd,
        server_id,
        lambda table: table.__setitem__("bearer_token_env_var", env_var),
    )


def add_env_var(cwd: Path, server_id: str, env_var: str) -> str:
    """Add an env_vars string override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        env_var: Environment variable name.

    Returns:
        Updated server id.
    """
    return _mutate_server(cwd, server_id, lambda table: _add_env_var(table, env_var))


def remove_env_var(cwd: Path, server_id: str, env_var: str) -> str:
    """Remove an env_vars string override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        env_var: Environment variable name.

    Returns:
        Updated server id.
    """
    return _mutate_server(cwd, server_id, lambda table: _remove_env_var(table, env_var))


def set_env_header(cwd: Path, server_id: str, header: str, env_var: str) -> str:
    """Set an env_http_headers override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        header: Header name.
        env_var: Environment variable name.

    Returns:
        Updated server id.
    """
    return _mutate_server(
        cwd,
        server_id,
        lambda table: _env_headers(table).__setitem__(header, env_var),
    )


def unset_env_header(cwd: Path, server_id: str, header: str) -> str:
    """Remove an env_http_headers override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        header: Header name.

    Returns:
        Updated server id.
    """
    return _mutate_server(
        cwd,
        server_id,
        lambda table: _env_headers(table).pop(header, None),
    )


def set_field(cwd: Path, server_id: str, field: str, raw_value: str) -> str:
    """Set one allowlisted MCP field from a TOML literal.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        field: Allowlisted field name.
        raw_value: TOML literal text.

    Returns:
        Updated server id.
    """
    if field not in SET_FIELD_NAMES:
        raise CommandError(f"Unsupported MCP field for set-field: {field}")
    value = parse_value(raw_value)
    validate_field(server_id, field, value)
    return _mutate_server(cwd, server_id, lambda table: table.__setitem__(field, value))


def _mutate_server(cwd: Path, server_id: str, mutation: Mutation) -> str:
    """Mutate one server override in project config.

    Args:
        cwd: Project directory.
        server_id: MCP server id.
        mutation: Callable that mutates the server table.

    Returns:
        Updated server id.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    server = _ensure_server(config, server_id)
    mutation(server)
    validate_override(server_id, server, strict=True)
    write_toml_file(config_path(cwd), config)
    return server_id


def _ensure_server(
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


def _add_env_var(table: MutableMapping[str, Any], env_var: str) -> None:
    """Add an env var to an override table.

    Args:
        table: Server override table.
        env_var: Env var name.
    """
    values = _env_var_values(table)
    if env_var not in values:
        values.append(env_var)
    table["env_vars"] = values


def _remove_env_var(table: MutableMapping[str, Any], env_var: str) -> None:
    """Remove an env var from an override table.

    Args:
        table: Server override table.
        env_var: Env var name.
    """
    values = _env_var_values(table)
    table["env_vars"] = [value for value in values if value != env_var]


def _env_var_values(table: MutableMapping[str, Any]) -> list[str]:
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


def _env_headers(table: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Return or create the env_http_headers override table.

    Args:
        table: Server override table.

    Returns:
        Mutable env_http_headers table.
    """
    return ensure_toml_table(table, "env_http_headers", "env_http_headers must be a string map")
