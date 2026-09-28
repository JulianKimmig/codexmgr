"""Build reusable-guide display items for the TUI."""

from ..guides.config import guide_lists
from ..guides.listing import GuideListItem, guide_list_items_for_state
from ..guides.tree import GuideTreeNode, build_guide_tree
from .models import ManagedItem
from .state import StagedConfig


def guide_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged reusable guide items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    return [_managed_item(item) for item in _staged_guide_items(staged)]


def guide_tree_items(staged: StagedConfig) -> list[GuideTreeNode]:
    """Return staged reusable guide items as hierarchical nodes.

    Args:
        staged: Staged project configuration.

    Returns:
        Root-level guide tree nodes.
    """
    return build_guide_tree(_staged_guide_items(staged))


def _staged_guide_items(staged: StagedConfig) -> list[GuideListItem]:
    """Return flat guide items for the staged config.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted guide list items.
    """
    enabled, disabled = guide_lists(staged.config)
    return guide_list_items_for_state(enabled, disabled, staged.codexmgr_home)


def _managed_item(item: GuideListItem) -> ManagedItem:
    """Convert a reusable-guide item to a TUI item.

    Args:
        item: Guide item from the shared listing model.

    Returns:
        TUI display item with the canonical guide ref as its value.
    """
    return ManagedItem(item.name, item.state, item.missing, value=item.name)
