"""Read-only listing helpers for managed Codex hook bundles."""

from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file
from .config import hook_lists
from .sources import available_hook_names, resolve_hook_source


@dataclass(frozen=True)
class HookListItem:
    """Display state for one known hook bundle.

    Attributes:
        name: Hook bundle name or configured reference.
        state: One of ``available``, ``enabled``, or ``disabled``.
        missing: Whether a configured hook bundle does not resolve.
    """

    name: str
    state: str
    missing: bool = False


def hook_list_lines(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Build display lines for available and configured hooks.

    Args:
        cwd: Project directory whose configured hooks should be read.
        codexmgr_home: codexmgr home containing hook bundles.

    Returns:
        Sorted hook list lines suitable for CLI output.
    """
    return [_format_item(item) for item in list_hook_items(cwd, codexmgr_home)]


def list_hook_items(cwd: Path, codexmgr_home: Path) -> list[HookListItem]:
    """List available and configured hooks with project state.

    Args:
        cwd: Project directory whose configured hooks should be read.
        codexmgr_home: codexmgr home containing hook bundles.

    Returns:
        Hook items sorted by displayed name.
    """
    enabled, disabled = configured_hook_lists(cwd)
    available = set(available_hook_names(codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [_hook_item(name, enabled, disabled, available, codexmgr_home) for name in names]


def configured_hook_lists(cwd: Path) -> tuple[list[str], list[str]]:
    """Read configured enabled and disabled hook bundle references.

    Args:
        cwd: Project directory whose codexmgr.toml should be read when present.

    Returns:
        Enabled and disabled hook bundle name lists.
    """
    return hook_lists(load_optional_toml_file(config_path(cwd)))


def missing_enabled_hooks(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Return enabled hook bundle references that do not resolve.

    Args:
        cwd: Project directory whose configured hooks should be read.
        codexmgr_home: codexmgr home containing hook bundles.

    Returns:
        Enabled hook bundle names that are currently missing.
    """
    enabled, _ = configured_hook_lists(cwd)
    return [name for name in enabled if resolve_hook_source(name, codexmgr_home) is None]


def _hook_item(
    name: str,
    enabled: list[str],
    disabled: list[str],
    available: set[str],
    codexmgr_home: Path,
) -> HookListItem:
    """Build one hook list item.

    Args:
        name: Hook bundle name or configured reference.
        enabled: Enabled hook bundle names.
        disabled: Disabled hook bundle names.
        available: Available named hook bundles.
        codexmgr_home: codexmgr home containing hook bundles.

    Returns:
        Display item for the hook.
    """
    if name in enabled:
        return HookListItem(name, "enabled", _is_missing(name, codexmgr_home))
    if name in disabled:
        return HookListItem(name, "disabled", _is_missing(name, codexmgr_home))
    return HookListItem(name, "available", name not in available)


def _is_missing(name: str, codexmgr_home: Path) -> bool:
    """Return whether a configured hook bundle is missing.

    Args:
        name: Configured hook bundle name.
        codexmgr_home: codexmgr home containing hook bundles.

    Returns:
        True when no hooks.json file resolves for the reference.
    """
    return resolve_hook_source(name, codexmgr_home) is None


def _format_item(item: HookListItem) -> str:
    """Format one hook list item.

    Args:
        item: Hook list item to format.

    Returns:
        Human-readable CLI line.
    """
    suffix = " (missing)" if item.missing else ""
    return f"{item.state} {item.name}{suffix}"
