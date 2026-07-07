"""Textual tree rendering helpers for reusable rules."""

from rich.text import Text
from textual.widgets import Tree
from textual.widgets._tree import TreeNode

from ..rules.tree import RuleTreeNode
from .models import ManagedItem
from .rendering import STATE_STYLES
from .rule_items import rule_tree_items
from .state import StagedConfig


def populate_rule_tree(
    tree: Tree[ManagedItem | None],
    staged: StagedConfig,
) -> list[ManagedItem]:
    """Populate a Textual tree with staged reusable rules.

    Args:
        tree: Tree widget to replace with current rule nodes.
        staged: Staged project configuration.

    Returns:
        Flat list of selectable rule items rendered into the tree.
    """
    rendered: list[ManagedItem] = []
    tree.show_root = False
    tree.root.remove_children()
    tree.root.expand()
    for node in rule_tree_items(staged):
        _add_tree_node(tree.root, node, rendered)
    return rendered


def rule_item_from_tree_node(node: TreeNode[ManagedItem | None]) -> ManagedItem | None:
    """Return the selectable item attached to a Textual tree node.

    Args:
        node: Textual tree node under the reusable-rules tree.

    Returns:
        Managed item for selectable rule refs, otherwise ``None``.
    """
    return node.data if isinstance(node.data, ManagedItem) else None


def _add_tree_node(
    parent: TreeNode[ManagedItem | None],
    node: RuleTreeNode,
    rendered: list[ManagedItem],
) -> None:
    """Add one reusable-rule node and descendants to a Textual tree.

    Args:
        parent: Parent Textual tree node.
        node: Shared rule tree node to render.
        rendered: Flat list that receives selectable items.
    """
    item = _managed_item(node)
    if item is not None:
        rendered.append(item)
    if node.children:
        tree_node = parent.add(
            _node_label(node, item),
            item,
            expand=_expand_by_default(node),
        )
    else:
        tree_node = parent.add_leaf(_node_label(node, item), item)
    for child in node.children:
        _add_tree_node(tree_node, child, rendered)


def _managed_item(node: RuleTreeNode) -> ManagedItem | None:
    """Convert a selectable rule tree node to a managed TUI item.

    Args:
        node: Rule tree node to convert.

    Returns:
        Managed item for selectable nodes, otherwise ``None``.
    """
    if node.item is None:
        return None
    return ManagedItem(
        node.item.name,
        node.item.state,
        node.item.missing,
        value=node.item.name,
    )


def _node_label(node: RuleTreeNode, item: ManagedItem | None) -> Text:
    """Build the rich label for one reusable-rule tree node.

    Args:
        node: Rule tree node being rendered.
        item: Managed item for selectable nodes, otherwise ``None``.

    Returns:
        Rich label for Textual's tree widget.
    """
    label = Text(node.label, style="dim" if item is None else "")
    if item is None:
        return label
    label.append("  ")
    label.append(item.state, style=STATE_STYLES.get(item.state, "white"))
    if item.missing:
        label.append("  missing", style="bold red")
    return label


def _expand_by_default(node: RuleTreeNode) -> bool:
    """Return whether a folder node should initially expand.

    Args:
        node: Rule tree node with children.

    Returns:
        True when expansion is needed to reveal configured or missing children.
    """
    if node.item is None:
        return True
    return any(_contains_configured_rule(child) for child in node.children)


def _contains_configured_rule(node: RuleTreeNode) -> bool:
    """Return whether a node contains configured or missing rule state.

    Args:
        node: Rule tree node to inspect.

    Returns:
        True when the node or any descendant is not plain available state.
    """
    if node.item is None:
        return True
    if node.item.state != "available" or node.item.missing:
        return True
    return any(_contains_configured_rule(child) for child in node.children)
