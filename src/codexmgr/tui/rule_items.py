"""Build reusable-rule display items for the TUI."""

from ..rules.config import rule_lists
from ..rules.sources import available_rule_refs, canonical_rule_ref_if_exists
from .models import ManagedItem
from .state import StagedConfig


def rule_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged reusable rule items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    enabled, disabled = rule_lists(staged.config)
    available = set(available_rule_refs(staged.codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [
        ManagedItem(name, _state(name, enabled, disabled), _missing_rule(name, staged))
        for name in names
    ]


def _state(name: str, enabled: list[str], disabled: list[str]) -> str:
    """Return enabled, disabled, or available for a rule item.

    Args:
        name: Rule reference.
        enabled: Enabled rule refs.
        disabled: Disabled rule refs.

    Returns:
        Display state.
    """
    if name in enabled:
        return "enabled"
    if name in disabled:
        return "disabled"
    return "available"


def _missing_rule(name: str, staged: StagedConfig) -> bool:
    """Return whether a configured rule ref is missing.

    Args:
        name: Rule reference.
        staged: Staged project configuration.

    Returns:
        True when a configured rule ref does not resolve.
    """
    enabled, disabled = rule_lists(staged.config)
    if name not in enabled and name not in disabled:
        return False
    return canonical_rule_ref_if_exists(name, staged.codexmgr_home) is None
