"""Focus helpers for Textual TUI resource widgets."""

from collections.abc import Sequence

from textual.widgets import SelectionList, Tree
from textual.widgets._tree import TreeNode

from .models import ManagedItem
from .rule_tree import rule_item_from_tree_node


def highlighted_list_item(
    items: SelectionList[str],
    rendered_items: Sequence[ManagedItem],
) -> ManagedItem | None:
    """Return the managed item highlighted in a selection list.

    Args:
        items: Selection-list widget containing rendered resources.
        rendered_items: Managed items represented by the widget options.

    Returns:
        Highlighted managed item, or None when no option is highlighted.
    """
    option = items.highlighted_option
    if option is None:
        return None
    return next(
        (
            item
            for item in rendered_items
            if item.selection_value() == option.value
        ),
        None,
    )


def highlighted_rule_item(tree: Tree[ManagedItem | None]) -> ManagedItem | None:
    """Return the managed item highlighted in a reusable-rules tree.

    Args:
        tree: Rules tree widget containing managed rule data.

    Returns:
        Highlighted managed item, or None when the cursor is on a folder node.
    """
    return rule_item_from_tree_node(tree.cursor_node)


def restore_selection_list_focus(
    items: SelectionList[str],
    selection_value: str | None,
) -> None:
    """Restore a selection-list highlight after options are rebuilt.

    Args:
        items: Selection-list widget with current options.
        selection_value: Stable value to restore, or None for initial focus.

    Returns:
        None.
    """
    if not items.options:
        return
    if selection_value is not None:
        for index, option in enumerate(items.options):
            if option.value == selection_value:
                items.highlighted = index
                return
    items.highlighted = 0


def restore_rule_tree_focus(
    tree: Tree[ManagedItem | None],
    selection_value: str | None,
) -> None:
    """Restore a rules-tree cursor after nodes are rebuilt.

    Args:
        tree: Rules tree widget with current nodes.
        selection_value: Stable rule value to restore, or None for initial focus.

    Returns:
        None.
    """
    if selection_value is not None:
        node = _find_tree_node(tree.root, selection_value)
        if node is not None:
            _expand_ancestors(node)
            tree.select_node(node)
            return
    if tree.root.children:
        tree.select_node(tree.root.children[0])


def _find_tree_node(
    node: TreeNode[ManagedItem | None],
    selection_value: str,
) -> TreeNode[ManagedItem | None] | None:
    """Find a tree node by its managed item's stable value.

    Args:
        node: Tree node where the search starts.
        selection_value: Stable selection value to match.

    Returns:
        Matching tree node, or None when the subtree has no match.
    """
    item = rule_item_from_tree_node(node)
    if item is not None and item.selection_value() == selection_value:
        return node
    for child in node.children:
        found = _find_tree_node(child, selection_value)
        if found is not None:
            return found
    return None


def _expand_ancestors(node: TreeNode[ManagedItem | None]) -> None:
    """Expand every parent needed to reveal a tree node.

    Args:
        node: Tree node that should remain visible after selection.

    Returns:
        None.
    """
    parent = node.parent
    while parent is not None:
        parent.expand()
        parent = parent.parent
