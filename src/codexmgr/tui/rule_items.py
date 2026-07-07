"""Build reusable-rule display items for the TUI."""

from ..rules.config import rule_lists
from ..rules.listing import RuleListItem, rule_list_items_for_state
from ..rules.tree import RuleTreeNode, build_rule_tree
from .models import ManagedItem
from .state import StagedConfig


def rule_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged reusable rule items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    return [_managed_item(item) for item in _staged_rule_items(staged)]


def rule_tree_items(staged: StagedConfig) -> list[RuleTreeNode]:
    """Return staged reusable rule items as hierarchical nodes.

    Args:
        staged: Staged project configuration.

    Returns:
        Root-level rule tree nodes.
    """
    return build_rule_tree(_staged_rule_items(staged))


def _staged_rule_items(staged: StagedConfig) -> list[RuleListItem]:
    """Return flat rule items for the staged config.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted rule list items.
    """
    enabled, disabled = rule_lists(staged.config)
    return rule_list_items_for_state(enabled, disabled, staged.codexmgr_home)


def _managed_item(item: RuleListItem) -> ManagedItem:
    """Convert a reusable-rule item to a TUI item.

    Args:
        item: Rule item from the shared listing model.

    Returns:
        TUI display item with the canonical rule ref as its value.
    """
    return ManagedItem(item.name, item.state, item.missing, value=item.name)
