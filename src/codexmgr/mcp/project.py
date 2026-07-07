"""Manage reusable MCP source references in project configuration."""

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.paths import config_path
from ..core.toml_io import (
    ensure_toml_table,
    load_optional_toml_file,
    plain_toml_value,
    write_toml_file,
)
from ..project.config import require_codex_dir
from .sources import is_bare_mcp_source_name, load_mcp_sources, require_mcp_source


def enable_mcp_sources(names: list[str], cwd: Path, codexmgr_home: Path) -> list[str]:
    """Enable reusable MCP sources for a project.

    Args:
        names: Bare MCP source names to enable.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: Codexmgr home directory containing source files.

    Returns:
        Enabled source names.
    """
    return _mutate_mcp_sources(names, cwd, codexmgr_home, enabled=True)


def disable_mcp_sources(names: list[str], cwd: Path, codexmgr_home: Path) -> list[str]:
    """Disable reusable MCP sources for a project.

    Args:
        names: Bare MCP source names to remove from the project.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: Codexmgr home directory used to validate remaining sources.

    Returns:
        Disabled source names.
    """
    return _mutate_mcp_sources(names, cwd, codexmgr_home, enabled=False)


def mcp_source_names(config: Mapping[str, Any]) -> list[str]:
    """Read enabled reusable MCP source names from project config.

    Args:
        config: Parsed project codexmgr configuration.

    Returns:
        Enabled reusable MCP source names.
    """
    mcp = config.get("mcp", {})
    if not isinstance(mcp, Mapping):
        raise CommandError("codexmgr.toml [mcp] must be a table")
    return _string_list(mcp, "enabled")


def set_mcp_source_enabled_in_config(
    config: MutableMapping[str, Any],
    name: str,
    *,
    enabled: bool,
) -> str:
    """Set one reusable MCP source in a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        name: MCP source name to add or remove.
        enabled: Whether the source should be present.

    Returns:
        Updated source name.
    """
    _validate_source_name(name)
    enabled_sources = mcp_source_names(config)
    if enabled:
        enabled_sources = _append_once(enabled_sources, name)
    else:
        enabled_sources = _without(enabled_sources, name)
    _set_mcp_sources(config, enabled_sources)
    return name


def _mutate_mcp_sources(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> list[str]:
    """Apply reusable MCP source mutations with one config write.

    Args:
        names: Source names to update.
        cwd: Project directory whose config should be changed.
        codexmgr_home: Codexmgr home directory containing source files.
        enabled: Whether to add or remove source names.

    Returns:
        Updated source names.
    """
    require_codex_dir(cwd)
    for name in names:
        _validate_source_name(name)
        if enabled:
            require_mcp_source(name, codexmgr_home)
    config = load_optional_toml_file(config_path(cwd))
    for name in names:
        set_mcp_source_enabled_in_config(config, name, enabled=enabled)
    load_mcp_sources(mcp_source_names(config), codexmgr_home)
    write_toml_file(config_path(cwd), config)
    return list(names)


def _set_mcp_sources(config: MutableMapping[str, Any], enabled: list[str]) -> None:
    """Write enabled reusable MCP source names into project config.

    Args:
        config: Parsed project config to mutate.
        enabled: Source names to write.
    """
    mcp = ensure_toml_table(config, "mcp", "codexmgr.toml [mcp] must be a table")
    mcp["enabled"] = enabled


def _string_list(table: Mapping[str, Any], key: str) -> list[str]:
    """Read a string list from an MCP project config table.

    Args:
        table: TOML table to inspect.
        key: Field name to read.

    Returns:
        A shallow copy of the configured string list.
    """
    values = plain_toml_value(table.get(key, []))
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise CommandError(f"codexmgr.toml mcp.{key} must be a list of strings")
    return list(values)


def _validate_source_name(name: str) -> None:
    """Require a bare MCP source name.

    Args:
        name: Source name to validate.
    """
    if not is_bare_mcp_source_name(name):
        raise CommandError(f"MCP source name must be a bare name: {name}")


def _append_once(values: list[str], value: str) -> list[str]:
    """Append a value only when it is absent.

    Args:
        values: Existing values.
        value: Value to append.

    Returns:
        A list containing the value once.
    """
    if value in values:
        return values
    return [*values, value]


def _without(values: list[str], value: str) -> list[str]:
    """Remove all matching values.

    Args:
        values: Existing values.
        value: Value to remove.

    Returns:
        Filtered list.
    """
    return [item for item in values if item != value]
