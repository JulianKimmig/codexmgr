"""Manage reusable guide enable and disable lists in project config."""

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import (
    ensure_toml_table,
    plain_toml_value,
)
from .sources import (
    canonical_guide_ref,
    canonical_guide_ref_if_exists,
    normalize_missing_guide_ref,
)


def set_guide_state_in_config(
    config: MutableMapping[str, Any],
    ref: str,
    codexmgr_home: Path,
    *,
    enabled: bool,
) -> str:
    """Set one guide reference in a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        ref: Guide file or folder reference.
        codexmgr_home: Codexmgr home containing source guides.
        enabled: Desired guide state.

    Returns:
        Canonical guide reference that was updated.
    """
    canonical = _canonical_for_state(ref, codexmgr_home, enabled=enabled).value
    enabled_guides, disabled_guides = guide_lists(config)
    enabled_guides = [_canonical_for_state(item, codexmgr_home, enabled=False).value for item in enabled_guides]
    disabled_guides = [_canonical_for_state(item, codexmgr_home, enabled=False).value for item in disabled_guides]
    if enabled:
        enabled_guides = _append_once(enabled_guides, canonical)
        disabled_guides = _without(disabled_guides, canonical)
    else:
        disabled_guides = _append_once(disabled_guides, canonical)
        enabled_guides = _without(enabled_guides, canonical)
    _set_guide_lists(config, enabled_guides, disabled_guides)
    return canonical


def remove_guide(config: MutableMapping[str, Any], ref: str, codexmgr_home: Path) -> None:
    """Clear an explicit selection without changing inherited folder selection.

    Args:
        config: Staged project document.
        ref: Exact file or folder selector to clear.
        codexmgr_home: Manager store used to canonicalize folder references.
    """
    canonical = _canonical_for_state(ref, codexmgr_home, enabled=False).value
    if "guides" not in config:
        return
    enabled, disabled = guide_lists(config)
    values = [[item for item in refs if _canonical_for_state(item, codexmgr_home, enabled=False).value != canonical]
              for refs in (enabled, disabled)]
    _set_guide_lists(config, *values)


def guide_reference_states(config: Mapping[str, Any], refs: list[str], codexmgr_home: Path) -> list[str]:
    """Return explicit canonical selector states for package and profile entries.

    Args:
        config: Project configuration containing optional guide selections.
        refs: Package guide references to inspect.
        codexmgr_home: Manager store used to resolve directory aliases.

    Returns:
        Enabled, disabled, or available for each selector.
    """
    enabled, disabled = ({_canonical_for_state(ref, codexmgr_home, enabled=False).value for ref in values}
                         for values in guide_lists(config))
    names = [_canonical_for_state(ref, codexmgr_home, enabled=False).value for ref in refs]
    return ["disabled" if name in disabled else "enabled" if name in enabled else "available" for name in names]


def guide_lists(config: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """Read enabled and disabled guide lists from project config.

    Args:
        config: Parsed project codexmgr configuration.

    Returns:
        Enabled and disabled guide references.
    """
    guides = config.get("guides", {})
    if not isinstance(guides, Mapping):
        raise CommandError("codexmgr.toml [guides] must be a table")
    return _string_list(guides, "enabled"), _string_list(guides, "disabled")


def _canonical_for_state(ref: str, codexmgr_home: Path, *, enabled: bool):
    """Return canonical guide ref for a config mutation.

    Args:
        ref: User-supplied guide reference.
        codexmgr_home: Codexmgr home containing source guides.
        enabled: Whether missing refs should be rejected.

    Returns:
        Canonical guide reference object.
    """
    if enabled:
        return canonical_guide_ref(ref, codexmgr_home)
    return canonical_guide_ref_if_exists(ref, codexmgr_home) or normalize_missing_guide_ref(ref)


def _string_list(table: Mapping[str, Any], key: str) -> list[str]:
    """Read one guides string-list field.

    Args:
        table: TOML table to inspect.
        key: Field name to read.

    Returns:
        A shallow copy of the configured string list.
    """
    values = plain_toml_value(table.get(key, []))
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise CommandError(f"codexmgr.toml guides.{key} must be a list of strings")
    return list(values)


def _set_guide_lists(
    config: MutableMapping[str, Any],
    enabled: list[str],
    disabled: list[str],
) -> None:
    """Write guide state lists into project config.

    Args:
        config: Parsed project config to mutate.
        enabled: Enabled guide refs to write.
        disabled: Disabled guide refs to write.
    """
    guides = ensure_toml_table(config, "guides", "codexmgr.toml [guides] must be a table")
    guides["enabled"] = enabled
    guides["disabled"] = disabled


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
