"""Render selectable skill groups while preserving folder expansion state."""

from pathlib import PurePosixPath

from rich.text import Text
from textual.widgets import Tree
from textual.widgets._tree import TreeNode

from ..skills.discovery import is_store_reference
from .items import skill_items
from .models import ManagedItem
from .rendering import STATE_STYLES
from .state import StagedConfig


def populate_skill_tree(tree: Tree[ManagedItem | None], staged: StagedConfig) -> list[ManagedItem]:
    """Rebuild a skill tree with aggregate group states and retained expansion.

    Args:
        tree: Skill tree widget whose nodes should be replaced.
        staged: In-memory project configuration and skill-store roots.

    Returns:
        All selectable leaf and group items represented by the tree.
    """
    expanded = _expanded_values(tree.root)
    leaves = skill_items(staged)
    groups: dict[str, list[ManagedItem]] = {}
    for item in leaves:
        if is_store_reference(item.name):
            parts = item.name.split("/")
            for depth in range(1, len(parts)):
                group = "/".join(parts[:depth]) + "/"
                groups.setdefault(group, []).append(item)
    rendered = leaves + [_group_item(group, members) for group, members in groups.items()]
    children: dict[str, list[ManagedItem]] = {}
    for item in rendered:
        parent = ""
        reference = item.name.rstrip("/")
        if is_store_reference(reference) and "/" in reference:
            parent = reference.rsplit("/", 1)[0] + "/"
        children.setdefault(parent, []).append(item)
    tree.show_root = False
    tree.root.remove_children()
    tree.root.expand()
    _add_children(tree.root, "", children, expanded)
    return rendered


def _group_item(reference: str, members: list[ManagedItem]) -> ManagedItem:
    """Aggregate descendant states into one selectable group item.

    Args:
        reference: Canonical trailing-slash group path.
        members: All leaf descendants, including missing configured skills.

    Returns:
        Group item with a common state or mixed when descendants disagree.
    """
    states = {item.state for item in members}
    return ManagedItem(
        reference, next(iter(states)) if len(states) == 1 else "mixed",
        any(item.missing for item in members), detail=f"{len(members)} skills",
    )


def _add_children(
    parent: TreeNode[ManagedItem | None], reference: str,
    children: dict[str, list[ManagedItem]], expanded: set[str],
) -> None:
    """Attach sorted children and recurse into source grouping folders.

    Args:
        parent: Rendered parent receiving nodes.
        reference: Parent group reference, or empty for the root.
        children: Items indexed by their immediate parent group.
        expanded: Group references expanded before the rebuild.
    """
    for item in sorted(children.get(reference, []), key=lambda item: item.name.lower()):
        label = _label(item)
        if item.name in children:
            node = parent.add(label, item, expand=item.name in expanded)
            _add_children(node, item.name, children, expanded)
        else:
            parent.add_leaf(label, item)


def _label(item: ManagedItem) -> Text:
    """Build a compact label without losing an explicit path's identity.

    Args:
        item: Individual skill or synthetic group to display.

    Returns:
        Rich label containing the basename, state, and missing indicator.
    """
    name = item.name
    if is_store_reference(name.rstrip("/")):
        name = PurePosixPath(name).name + ("/" if name.endswith("/") else "")
    label = Text(name)
    label.append(f"  {item.state}", style=STATE_STYLES.get(item.state, "white"))
    if item.detail:
        label.append(f"  {item.detail}", style="dim")
    if item.missing:
        label.append("  missing", style="bold red")
    return label


def _expanded_values(node: TreeNode[ManagedItem | None]) -> set[str]:
    """Collect expanded group identities, including descendants of closed groups.

    Args:
        node: Existing root or subtree to inspect before rebuilding.

    Returns:
        Stable values for every expanded managed node.
    """
    values = {node.data.selection_value()} if node.data is not None and node.is_expanded else set()
    for child in node.children:
        values.update(_expanded_values(child))
    return values
