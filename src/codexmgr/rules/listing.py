"""Read-only listing helpers for reusable rule files."""

from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file
from .config import rule_lists
from .sources import available_rule_refs, canonical_rule_ref_if_exists


@dataclass(frozen=True)
class RuleListItem:
    """Display state for one known or configured rule reference.

    Attributes:
        name: Canonical rule file or folder reference.
        state: One of ``available``, ``enabled``, or ``disabled``.
        missing: Whether a configured reference does not currently resolve.
    """

    name: str
    state: str
    missing: bool = False


def rule_list_lines(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Build CLI display lines for reusable rules.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Sorted rule list lines.
    """
    return [_format_item(item) for item in list_rule_items(cwd, codexmgr_home)]


def list_rule_items(cwd: Path, codexmgr_home: Path) -> list[RuleListItem]:
    """List available and configured rule refs with project state.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Sorted display items.
    """
    enabled, disabled = configured_rule_lists(cwd)
    available = set(available_rule_refs(codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [_rule_item(name, enabled, disabled, available, codexmgr_home) for name in names]


def configured_rule_lists(cwd: Path) -> tuple[list[str], list[str]]:
    """Read configured enabled and disabled rule refs.

    Args:
        cwd: Project directory whose codexmgr.toml should be read.

    Returns:
        Enabled and disabled rule refs.
    """
    return rule_lists(load_optional_toml_file(config_path(cwd)))


def missing_enabled_rules(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Return enabled rules that do not currently resolve.

    Args:
        cwd: Project directory whose config should be read.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Missing enabled rule refs.
    """
    enabled, _ = configured_rule_lists(cwd)
    return [
        ref
        for ref in enabled
        if canonical_rule_ref_if_exists(ref, codexmgr_home) is None
    ]


def _rule_item(
    name: str,
    enabled: list[str],
    disabled: list[str],
    available: set[str],
    codexmgr_home: Path,
) -> RuleListItem:
    """Build one rule list item.

    Args:
        name: Rule reference to display.
        enabled: Enabled configured refs.
        disabled: Disabled configured refs.
        available: Available source refs.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Display item.
    """
    if name in enabled:
        return RuleListItem(name, "enabled", _is_missing(name, codexmgr_home))
    if name in disabled:
        return RuleListItem(name, "disabled", _is_missing(name, codexmgr_home))
    return RuleListItem(name, "available", name not in available)


def _is_missing(name: str, codexmgr_home: Path) -> bool:
    """Return whether a configured rule ref is missing.

    Args:
        name: Configured rule reference.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        True when no matching source exists.
    """
    return canonical_rule_ref_if_exists(name, codexmgr_home) is None


def _format_item(item: RuleListItem) -> str:
    """Format one rule list item.

    Args:
        item: Rule display item.

    Returns:
        Human-readable CLI line.
    """
    suffix = " (missing)" if item.missing else ""
    return f"{item.state} {item.name}{suffix}"
