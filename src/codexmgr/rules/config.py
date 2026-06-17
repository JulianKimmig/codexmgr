"""Manage reusable rule enable and disable lists in project config."""

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
from .sources import (
    canonical_rule_ref,
    canonical_rule_ref_if_exists,
    normalize_missing_rule_ref,
)


def enable_rule(ref: str, cwd: Path, codexmgr_home: Path) -> str:
    """Enable one reusable rule reference.

    Args:
        ref: Rule file or folder reference.
        cwd: Project directory whose config should be updated.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Canonical enabled rule reference.
    """
    return _set_rule_state(ref, cwd, codexmgr_home, enabled=True)


def disable_rule(ref: str, cwd: Path, codexmgr_home: Path) -> str:
    """Disable one reusable rule reference.

    Args:
        ref: Rule file or folder reference.
        cwd: Project directory whose config should be updated.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Canonical disabled rule reference.
    """
    return _set_rule_state(ref, cwd, codexmgr_home, enabled=False)


def set_rule_state_in_config(
    config: MutableMapping[str, Any],
    ref: str,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> str:
    """Set one rule reference in a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        ref: Rule file or folder reference.
        codexmgr_home: Codexmgr home containing source rules.
        enabled: Desired rule state.

    Returns:
        Canonical rule reference that was updated.
    """
    canonical = _canonical_for_state(ref, codexmgr_home, enabled=enabled).value
    enabled_rules, disabled_rules = rule_lists(config)
    if enabled:
        enabled_rules = _append_once(enabled_rules, canonical)
        disabled_rules = _without(disabled_rules, canonical)
    else:
        disabled_rules = _append_once(disabled_rules, canonical)
        enabled_rules = _without(enabled_rules, canonical)
    _set_rule_lists(config, enabled_rules, disabled_rules)
    return canonical


def rule_lists(config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Read enabled and disabled rule lists from project config.

    Args:
        config: Parsed project codexmgr configuration.

    Returns:
        Enabled and disabled rule references.
    """
    rules = config.get("rules", {})
    if not isinstance(rules, Mapping):
        raise CommandError("codexmgr.toml [rules] must be a table")
    return _string_list(rules, "enabled"), _string_list(rules, "disabled")


def _set_rule_state(
    ref: str,
    cwd: Path,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> str:
    """Set one rule state in the project config file.

    Args:
        ref: Rule reference to update.
        cwd: Project directory whose config should be updated.
        codexmgr_home: Codexmgr home containing source rules.
        enabled: Desired state.

    Returns:
        Canonical rule reference that was updated.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    canonical = set_rule_state_in_config(config, ref, codexmgr_home, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return canonical


def _canonical_for_state(ref: str, codexmgr_home: Path, *, enabled: bool):
    """Return canonical rule ref for a config mutation.

    Args:
        ref: User-supplied rule reference.
        codexmgr_home: Codexmgr home containing source rules.
        enabled: Whether missing refs should be rejected.

    Returns:
        Canonical rule reference object.
    """
    if enabled:
        return canonical_rule_ref(ref, codexmgr_home)
    return canonical_rule_ref_if_exists(ref, codexmgr_home) or normalize_missing_rule_ref(ref)


def _string_list(table: Mapping[str, Any], key: str) -> list[str]:
    """Read one rules string-list field.

    Args:
        table: TOML table to inspect.
        key: Field name to read.

    Returns:
        A shallow copy of the configured string list.
    """
    values = plain_toml_value(table.get(key, []))
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise CommandError(f"codexmgr.toml rules.{key} must be a list of strings")
    return list(values)


def _set_rule_lists(
    config: MutableMapping[str, Any],
    enabled: list[str],
    disabled: list[str],
) -> None:
    """Write rule state lists into project config.

    Args:
        config: Parsed project config to mutate.
        enabled: Enabled rule refs to write.
        disabled: Disabled rule refs to write.
    """
    rules = ensure_toml_table(config, "rules", "codexmgr.toml [rules] must be a table")
    rules["enabled"] = enabled
    rules["disabled"] = disabled


def _append_once(values: list[str], value: str) -> list[str]:
    """Append a value unless already present.

    Args:
        values: Existing values.
        value: Candidate value.

    Returns:
        Updated list.
    """
    return values if value in values else [*values, value]


def _without(values: list[str], value: str) -> list[str]:
    """Remove exact matches from a list.

    Args:
        values: Existing values.
        value: Value to remove.

    Returns:
        Filtered list.
    """
    return [item for item in values if item != value]
