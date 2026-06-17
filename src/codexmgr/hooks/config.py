"""Manage hook enable and disable lists in project configuration."""

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
from .sources import require_hook_source


def enable_hook(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Add a hook bundle to hooks.enabled and remove it from disabled.

    Args:
        name: Bare hook bundle name to record in project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory used to validate the bundle.

    Returns:
        The hook bundle name that was enabled.
    """
    require_hook_source(name, codexmgr_home)
    return _set_hook_state(name, cwd, enabled=True)


def disable_hook(name: str, cwd: Path) -> str:
    """Add a hook bundle to hooks.disabled and remove it from enabled.

    Args:
        name: Bare hook bundle name to record in project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.

    Returns:
        The hook bundle name that was disabled.
    """
    return _set_hook_state(name, cwd, enabled=False)


def hook_lists(config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Read enabled and disabled hook lists from project config.

    Args:
        config: Parsed project codexmgr configuration.

    Returns:
        The enabled list and disabled list.
    """
    hooks = config.get("hooks", {})
    if not isinstance(hooks, Mapping):
        raise CommandError("codexmgr.toml [hooks] must be a table")
    return _string_list(hooks, "enabled"), _string_list(hooks, "disabled")


def _set_hook_state(name: str, cwd: Path, *, enabled: bool) -> str:
    """Set one hook bundle reference to enabled or disabled.

    Args:
        name: Bare hook bundle name to update.
        cwd: Project directory whose codexmgr.toml should be updated.
        enabled: Desired hook state.

    Returns:
        The updated hook bundle name.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    enabled_hooks, disabled_hooks = hook_lists(config)

    if enabled:
        enabled_hooks = _append_once(enabled_hooks, name)
        disabled_hooks = _without(disabled_hooks, name)
    else:
        disabled_hooks = _append_once(disabled_hooks, name)
        enabled_hooks = _without(enabled_hooks, name)

    _set_hook_lists(config, enabled_hooks, disabled_hooks)
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
        raise CommandError(f"codexmgr.toml hooks.{key} must be a list of strings")
    return list(values)


def _set_hook_lists(
    config: MutableMapping[str, Any],
    enabled: list[str],
    disabled: list[str],
) -> None:
    """Write enabled and disabled hook lists into project config.

    Args:
        config: Parsed project codexmgr configuration to mutate.
        enabled: Hook bundle names to write to hooks.enabled.
        disabled: Hook bundle names to write to hooks.disabled.
    """
    hooks = ensure_toml_table(config, "hooks", "codexmgr.toml [hooks] must be a table")
    hooks["enabled"] = enabled
    hooks["disabled"] = disabled


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
