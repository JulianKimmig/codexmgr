"""Read-only listing helpers for reusable guide files."""

from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file
from .config import guide_lists
from .sources import available_guide_refs, canonical_guide_ref_if_exists, normalize_missing_guide_ref


@dataclass(frozen=True)
class GuideListItem:
    """Display state for one known or configured guide reference.

    Attributes:
        name: Canonical guide file or folder reference.
        state: One of ``available``, ``enabled``, or ``disabled``.
        missing: Whether a configured reference does not currently resolve.
    """

    name: str
    state: str
    missing: bool = False


def guide_list_lines(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Build CLI display lines for reusable guides.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Sorted guide list lines.
    """
    from .tree import format_guide_tree_lines, guide_tree_nodes

    return format_guide_tree_lines(guide_tree_nodes(cwd, codexmgr_home))


def list_guide_items(cwd: Path, codexmgr_home: Path) -> list[GuideListItem]:
    """List available and configured guide refs with project state.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Sorted display items.
    """
    enabled, disabled = configured_guide_lists(cwd)
    return guide_list_items_for_state(enabled, disabled, codexmgr_home)


def guide_list_items_for_state(
    enabled: list[str],
    disabled: list[str],
    codexmgr_home: Path,
) -> list[GuideListItem]:
    """List available and configured guide refs for explicit guide state.

    Args:
        enabled: Enabled guide refs from a project or staged config.
        disabled: Disabled guide refs from a project or staged config.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Sorted display items.
    """
    available = set(available_guide_refs(codexmgr_home))
    enabled, disabled = [
        [(canonical_guide_ref_if_exists(ref, codexmgr_home) or normalize_missing_guide_ref(ref)).value for ref in refs]
        for refs in (enabled, disabled)
    ]
    names = sorted(available | set(enabled) | set(disabled))
    return [_guide_item(name, enabled, disabled, available, codexmgr_home) for name in names]


def configured_guide_lists(cwd: Path) -> tuple[list[str], list[str]]:
    """Read configured enabled and disabled guide refs.

    Args:
        cwd: Project directory whose codexmgr.toml should be read.

    Returns:
        Enabled and disabled guide refs.
    """
    return guide_lists(load_optional_toml_file(config_path(cwd)))


def missing_enabled_guides(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Return enabled guides that do not currently resolve.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Missing enabled guide refs.
    """
    enabled, _ = configured_guide_lists(cwd)
    return [
        ref
        for ref in enabled
        if canonical_guide_ref_if_exists(ref, codexmgr_home) is None
    ]


def _guide_item(
    name: str,
    enabled: list[str],
    disabled: list[str],
    available: set[str],
    codexmgr_home: Path,
) -> GuideListItem:
    """Build one guide list item.

    Args:
        name: Guide reference to display.
        enabled: Enabled configured refs.
        disabled: Disabled configured refs.
        available: Available source refs.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Display item.
    """
    if name in disabled:
        return GuideListItem(name, "disabled", _is_missing(name, codexmgr_home))
    if name in enabled:
        return GuideListItem(name, "enabled", _is_missing(name, codexmgr_home))
    return GuideListItem(name, "available", name not in available)


def _is_missing(name: str, codexmgr_home: Path) -> bool:
    """Return whether a configured guide ref is missing.

    Args:
        name: Configured guide reference.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        True when no matching source exists.
    """
    return canonical_guide_ref_if_exists(name, codexmgr_home) is None
