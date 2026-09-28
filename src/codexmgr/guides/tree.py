"""Build hierarchical display models for reusable guide references."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .listing import GuideListItem, list_guide_items


@dataclass(frozen=True)
class GuideTreeNode:
    """One node in the reusable-guide display tree.

    Attributes:
        path: Canonical full guide path for this node. Virtual grouping folders
            use a trailing slash path even though they are not selectable guides.
        label: Basename-style display label for the node.
        item: Guide item represented by this node, or ``None`` for a virtual
            grouping folder that exists only to hold missing descendants.
        children: Child nodes sorted by display label.
    """

    path: str
    label: str
    item: GuideListItem | None
    children: tuple["GuideTreeNode", ...] = ()

@dataclass
class _MutableGuideTreeNode:
    """Mutable node used while constructing the immutable guide tree.

    Attributes:
        path: Canonical full path for this node.
        label: Basename-style display label.
        item: Backing guide item when this node is selectable.
        children: Mutable child-node index by canonical path.
    """

    path: str
    label: str
    item: GuideListItem | None = None
    children: dict[str, "_MutableGuideTreeNode"] = field(default_factory=dict)


def guide_tree_nodes(cwd: Path, codexmgr_home: Path) -> list[GuideTreeNode]:
    """Build hierarchical guide nodes for a project.

    Args:
        cwd: Project directory whose configured guides should be read.
        codexmgr_home: Codexmgr home containing reusable guide sources.

    Returns:
        Root-level guide tree nodes.
    """
    return build_guide_tree(list_guide_items(cwd, codexmgr_home))


def build_guide_tree(items: Iterable[GuideListItem]) -> list[GuideTreeNode]:
    """Build immutable tree nodes from flat guide list items.

    Args:
        items: Flat guide items with canonical full refs.

    Returns:
        Root-level tree nodes containing virtual parents where needed.
    """
    roots: dict[str, _MutableGuideTreeNode] = {}
    for item in items:
        _insert_item(roots, item)
    return [_freeze_node(node) for node in _sorted_nodes(roots.values())]


def format_guide_tree_lines(nodes: Iterable[GuideTreeNode]) -> list[str]:
    """Format a guide tree for CLI display.

    Args:
        nodes: Root-level guide tree nodes.

    Returns:
        Indented CLI display lines.
    """
    lines: list[str] = []
    for node in nodes:
        _append_tree_lines(lines, node, depth=0)
    return lines


def _insert_item(
    roots: dict[str, _MutableGuideTreeNode],
    item: GuideListItem,
) -> None:
    """Insert one guide item into the mutable tree.

    Args:
        roots: Mutable root-node index.
        item: Guide item to insert.
    """
    children = roots
    parts = item.name.rstrip("/").split("/")
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        is_dir = not is_last or item.name.endswith("/")
        path = _node_path(parts[: index + 1], is_dir=is_dir)
        node = children.get(path)
        if node is None:
            node = _MutableGuideTreeNode(path, _node_label(part, is_dir=is_dir))
            children[path] = node
        if is_last:
            node.item = item
        children = node.children


def _node_path(parts: list[str], *, is_dir: bool) -> str:
    """Return the canonical path for tree parts.

    Args:
        parts: POSIX path parts up to the current node.
        is_dir: Whether the node represents a folder path.

    Returns:
        Canonical path for the node.
    """
    path = "/".join(parts)
    return f"{path}/" if is_dir else path


def _node_label(part: str, *, is_dir: bool) -> str:
    """Return the display label for one path part.

    Args:
        part: Last path component.
        is_dir: Whether the node represents a folder path.

    Returns:
        Basename display label.
    """
    return f"{part}/" if is_dir else part


def _freeze_node(node: _MutableGuideTreeNode) -> GuideTreeNode:
    """Convert a mutable node into an immutable guide tree node.

    Args:
        node: Mutable node to freeze.

    Returns:
        Immutable guide tree node.
    """
    return GuideTreeNode(
        node.path,
        node.label,
        node.item,
        tuple(_freeze_node(child) for child in _sorted_nodes(node.children.values())),
    )


def _sorted_nodes(nodes: Iterable[_MutableGuideTreeNode]) -> list[_MutableGuideTreeNode]:
    """Sort tree nodes by display label.

    Args:
        nodes: Mutable nodes to sort.

    Returns:
        Nodes sorted case-insensitively by display label.
    """
    return sorted(nodes, key=lambda node: (node.label.lower(), node.label))


def _append_tree_lines(lines: list[str], node: GuideTreeNode, *, depth: int) -> None:
    """Append one node and descendants to CLI output lines.

    Args:
        lines: Mutable output line list.
        node: Current guide tree node.
        depth: Indentation depth.
    """
    indent = "  " * depth
    lines.append(f"{indent}{_format_node(node)}")
    for child in node.children:
        _append_tree_lines(lines, child, depth=depth + 1)


def _format_node(node: GuideTreeNode) -> str:
    """Format one tree node for CLI output.

    Args:
        node: Guide tree node to format.

    Returns:
        Human-readable CLI line without indentation.
    """
    if node.item is None:
        return node.label
    suffix = " (missing)" if node.item.missing else ""
    return f"{node.item.state} {node.label}{suffix}"
