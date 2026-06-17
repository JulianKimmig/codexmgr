"""Manage custom-agent enable and disable lists in project configuration."""

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
from .sources import require_agent_source


def enable_agent(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Add a custom agent to agents.enabled and remove it from disabled.

    Args:
        name: Bare custom-agent name to record in project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory used to validate the agent.

    Returns:
        The custom-agent name that was enabled.
    """
    require_agent_source(name, codexmgr_home)
    return _set_agent_state(name, cwd, enabled=True)


def disable_agent(name: str, cwd: Path) -> str:
    """Add a custom agent to agents.disabled and remove it from enabled.

    Args:
        name: Bare custom-agent name to record in project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.

    Returns:
        The custom-agent name that was disabled.
    """
    return _set_agent_state(name, cwd, enabled=False)


def agent_lists(config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Read enabled and disabled custom-agent lists from project config.

    Args:
        config: Parsed project codexmgr configuration.

    Returns:
        Enabled and disabled custom-agent name lists.
    """
    agents = config.get("agents", {})
    if not isinstance(agents, Mapping):
        raise CommandError("codexmgr.toml [agents] must be a table")
    return _string_list(agents, "enabled"), _string_list(agents, "disabled")


def set_agent_state_in_config(
    config: MutableMapping[str, Any],
    name: str,
    *,
    enabled: bool,
) -> str:
    """Set one custom-agent state in a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        name: Bare custom-agent name to place in the requested state list.
        enabled: Desired state for the custom agent.

    Returns:
        The custom-agent name that was updated.
    """
    enabled_agents, disabled_agents = agent_lists(config)
    if enabled:
        enabled_agents = _append_once(enabled_agents, name)
        disabled_agents = _without(disabled_agents, name)
    else:
        disabled_agents = _append_once(disabled_agents, name)
        enabled_agents = _without(enabled_agents, name)
    _set_agent_lists(config, enabled_agents, disabled_agents)
    return name


def _set_agent_state(name: str, cwd: Path, *, enabled: bool) -> str:
    """Set one custom-agent reference to enabled or disabled.

    Args:
        name: Bare custom-agent name to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        enabled: Desired custom-agent state.

    Returns:
        The updated custom-agent name.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    set_agent_state_in_config(config, name, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return name


def _string_list(table: Mapping[str, Any], key: str) -> list[str]:
    """Read a string list from a project config table.

    Args:
        table: TOML table to inspect.
        key: List key to read.

    Returns:
        A shallow copy of the configured string list.
    """
    values = plain_toml_value(table.get(key, []))
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise CommandError(f"codexmgr.toml agents.{key} must be a list of strings")
    return list(values)


def _set_agent_lists(
    config: MutableMapping[str, Any],
    enabled: list[str],
    disabled: list[str],
) -> None:
    """Write enabled and disabled custom-agent lists into project config.

    Args:
        config: Parsed project codexmgr configuration to mutate.
        enabled: Custom-agent names to write to agents.enabled.
        disabled: Custom-agent names to write to agents.disabled.
    """
    agents = ensure_toml_table(config, "agents", "codexmgr.toml [agents] must be a table")
    agents["enabled"] = enabled
    agents["disabled"] = disabled


def _append_once(values: list[str], value: str) -> list[str]:
    """Append a value to a list only when it is absent.

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
    """Remove all matching values from a list.

    Args:
        values: Existing values.
        value: Value to remove.

    Returns:
        Filtered list.
    """
    return [item for item in values if item != value]
