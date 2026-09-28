"""Expand skill-group operations and reconcile bare aliases with source paths."""

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from .catalog import available_skill_names
from .config import _set_skill_lists, _skill_lists
from .discovery import is_store_reference


def normalized_skill_lists(
    config: Mapping[str, Any], cwd: Path, codex_home: Path, codexmgr_home: Path,
) -> tuple[list[str], list[str], list[str]]:
    """Return canonical enabled, disabled, and available skill references.

    Args:
        config: Current or staged project configuration.
        cwd: Project root.
        codex_home: Codex source store.
        codexmgr_home: Manager source store.

    Returns:
        State lists with unique bare aliases mapped to discovered qualified refs.
        Explicit paths and unresolved references retain their original identity.
    """
    available = available_skill_names(cwd, codex_home, codexmgr_home)
    enabled, disabled = _skill_lists(config)
    return (
        list(dict.fromkeys(_canonical(ref, available) for ref in enabled)),
        list(dict.fromkeys(_canonical(ref, available) for ref in disabled)),
        available,
    )


def expand_skill_references(
    references: list[str], config: Mapping[str, Any],
    cwd: Path, codex_home: Path, codexmgr_home: Path,
) -> list[str]:
    """Expand trailing-slash groups into individual current skill references.

    Args:
        references: Individual references or store-relative groups ending in /.
        config: Current state, including configured missing descendants.
        cwd: Project root.
        codex_home: Codex source store.
        codexmgr_home: Manager source store.

    Returns:
        Ordered unique leaf references; explicit paths are left unchanged.

    Raises:
        CommandError: When a requested group has no known descendants.
    """
    if not any(_is_group(reference) for reference in references):
        return list(dict.fromkeys(references))
    enabled, disabled, available = normalized_skill_lists(config, cwd, codex_home, codexmgr_home)
    known = sorted(set(available + enabled + disabled))
    expanded: list[str] = []
    for reference in references:
        if _is_group(reference):
            members = [ref for ref in known if is_store_reference(ref) and ref.startswith(reference)]
            if not members:
                raise CommandError(f"Skill group not found: {reference}")
            expanded.extend(members)
        else:
            expanded.append(reference)
    return list(dict.fromkeys(expanded))


def set_skill_references_state(
    config: MutableMapping[str, Any], references: list[str], state: str,
    cwd: Path, codex_home: Path, codexmgr_home: Path,
) -> None:
    """Set individual skills or current group descendants in a single batch.

    Args:
        config: Mutable project configuration.
        references: Skill references or trailing-slash groups.
        state: enabled, disabled, or available (remove explicit configuration).
        cwd: Project root.
        codex_home: Codex source store.
        codexmgr_home: Manager source store.
    """
    requested_groups = {ref for ref in references if _is_group(ref)}
    references = expand_skill_references(references, config, cwd, codex_home, codexmgr_home)
    available = (
        available_skill_names(cwd, codex_home, codexmgr_home)
        if any(is_store_reference(ref) for ref in references) else []
    )
    selected: dict[str, str] = {}
    for reference in references:
        selected.setdefault(_canonical(reference, available), reference)
    references = list(selected.values())
    enabled, disabled = _skill_lists(config)
    enabled = [ref for ref in enabled if ref not in requested_groups]
    disabled = [ref for ref in disabled if ref not in requested_groups]
    enabled = [
        ref for ref in enabled if _canonical(ref, available) not in selected
        or (state == "enabled" and ref in references)
    ]
    disabled = [
        ref for ref in disabled if _canonical(ref, available) not in selected
        or (state == "disabled" and ref in references)
    ]
    if state == "enabled":
        enabled.extend(ref for ref in references if ref not in enabled)
    elif state == "disabled":
        disabled.extend(ref for ref in references if ref not in disabled)
    elif state != "available":
        raise CommandError(f"Unsupported skill state: {state}")
    _set_skill_lists(config, enabled, disabled)


def skill_reference_states(
    config: Mapping[str, Any], references: list[str],
    cwd: Path, codex_home: Path, codexmgr_home: Path,
) -> list[str]:
    """Read individual descendant states for skill references or groups.

    Args:
        config: Current or staged project configuration.
        references: Individual skill references and trailing-slash groups.
        cwd: Project root used for source discovery.
        codex_home: Codex skill store.
        codexmgr_home: Manager skill store.

    Returns:
        Enabled, disabled, or available for each distinct selected identity.
    """
    references = expand_skill_references(references, config, cwd, codex_home, codexmgr_home)
    available = (
        available_skill_names(cwd, codex_home, codexmgr_home)
        if any(is_store_reference(ref) for ref in references) else []
    )
    enabled_refs, disabled_refs = _skill_lists(config)
    enabled = {_canonical(ref, available) for ref in enabled_refs}
    disabled = {_canonical(ref, available) for ref in disabled_refs}
    identities = dict.fromkeys(_canonical(ref, available) for ref in references)
    return [
        "enabled" if ref in enabled else "disabled" if ref in disabled else "available"
        for ref in identities
    ]


def _is_group(reference: str) -> bool:
    """Return whether a reference is a safe store group ending in a slash.

    Args:
        reference: Skill, group, or explicit filesystem path.

    Returns:
        True for store-relative groups; false for explicit paths and leaves.
    """
    return reference.endswith("/") and is_store_reference(reference[:-1])


def _canonical(reference: str, available: list[str]) -> str:
    """Map a unique bare reference to its displayed source path.

    Args:
        reference: Configured skill reference.
        available: Discovered canonical store references.

    Returns:
        Qualified reference when a single leaf matches; otherwise the input.
    """
    if reference in available or "/" in reference or not is_store_reference(reference):
        return reference
    matches = [ref for ref in available if Path(ref).name == reference]
    return matches[0] if len(matches) == 1 else reference
