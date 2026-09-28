"""Textual tree rendering helpers for reusable guides."""

from rich.text import Text
from textual.widgets import Tree
from textual.widgets._tree import TreeNode

from ..guides.tree import GuideTreeNode
from .models import ManagedItem
from .rendering import STATE_STYLES
from .guide_items import guide_tree_items
from .state import StagedConfig


def populate_guide_tree(
    tree: Tree[ManagedItem | None],
    staged: StagedConfig,
) -> list[ManagedItem]:
    """Populate a Textual tree with staged reusable guides.

    Args:
        tree: Tree widget to replace with current guide nodes.
        staged: Staged project configuration.

    Returns:
        Flat list of selectable guide items rendered into the tree.
    """
    rendered: list[ManagedItem] = []
    expanded = _expansion_states(tree.root)
    tree.show_root = False
    tree.root.remove_children()
    tree.root.expand()
    for node in guide_tree_items(staged):
        _add_tree_node(tree.root, node, rendered, expanded)
    return rendered


def _add_tree_node(
    parent: TreeNode[ManagedItem | None],
    node: GuideTreeNode,
    rendered: list[ManagedItem],
    expanded: dict[str, bool],
) -> None:
    """Add one reusable-guide node and descendants to a Textual tree.

    Args:
        parent: Parent Textual tree node.
        node: Shared guide tree node to render.
        rendered: Flat list that receives selectable items.
        expanded: Previous expansion flags keyed by full guide reference.
    """
    item = _managed_item(node)
    if item is not None:
        rendered.append(item)
    if node.children:
        tree_node = parent.add(
            _node_label(node, item),
            item,
            expand=expanded.get(node.path, node.item is None),
        )
    else:
        tree_node = parent.add_leaf(_node_label(node, item), item)
    for child in node.children:
        _add_tree_node(tree_node, child, rendered, expanded)


def _managed_item(node: GuideTreeNode) -> ManagedItem | None:
    """Convert a selectable guide tree node to a managed TUI item.

    Args:
        node: Guide tree node to convert.

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


def _node_label(node: GuideTreeNode, item: ManagedItem | None) -> Text:
    """Build the rich label for one reusable-guide tree node.

    Args:
        node: Guide tree node being rendered.
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


def _expansion_states(node: TreeNode[ManagedItem | None], prefix: str = "") -> dict[str, bool]:
    """Collect expansion flags for real and virtual guide folders.

    Args:
        node: Existing root or subtree before rebuilding.
        prefix: Full reference prefix for virtual grouping parents.

    Returns:
        Folder expansion states keyed by stable full references.
    """
    states: dict[str, bool] = {}
    for child in node.children:
        ref = child.data.selection_value() if child.data else prefix + str(child.label)
        states[ref] = child.is_expanded
        states.update(_expansion_states(child, ref))
    return states
