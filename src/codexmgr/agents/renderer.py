"""Render locked AGENTS.md template data into managed markdown."""

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..core.errors import CommandError


@dataclass
class RenderNode:
    """A merged markdown section from one or more TOML templates.

    Attributes:
        texts: Ordered text blocks attached to this markdown heading.
        children: Child headings keyed by their TOML table name.
    """

    texts: list[str] = field(default_factory=list)
    children: OrderedDict[str, "RenderNode"] = field(default_factory=OrderedDict)


def render_agents_markdown(sources: Mapping[str, Any]) -> str:
    """Render resolved AGENTS.md template data into markdown.

    Args:
        sources: Mapping of source identifiers to parsed TOML template tables.

    Returns:
        Markdown content for the managed AGENTS.md block.
    """
    root = RenderNode()

    for source_data in sources.values():
        if not isinstance(source_data, Mapping):
            raise CommandError("Source entries must be TOML tables")
        _merge_source(root, source_data)

    blocks = _render_children(root, 1)
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _merge_source(parent: RenderNode, source_data: Mapping[str, Any]) -> None:
    """Merge one parsed template source into the render tree.

    Args:
        parent: Root render node that receives template sections.
        source_data: Parsed TOML table for one configured source.
    """
    for name, value in source_data.items():
        if not isinstance(value, Mapping):
            raise CommandError(f"Template section must be a table: {name}")
        _merge_table(parent, (name,), value)


def _merge_table(root: RenderNode, path: tuple[str, ...], table: Mapping[str, Any]) -> None:
    """Merge a TOML table into the render tree.

    Args:
        root: Root render node that receives section data.
        path: Current TOML path being merged.
        table: Parsed TOML table at the current path.
    """
    node = _node_for_path(root, path)
    text = table.get("text")
    if text is not None:
        if not isinstance(text, str):
            raise CommandError(f"Text entry must be a string: {'.'.join(path)}")
        stripped = text.strip("\n")
        if stripped:
            node.texts.append(stripped)

    for name, value in table.items():
        if name == "text":
            continue
        if not isinstance(value, Mapping):
            section = ".".join((*path, name))
            raise CommandError(f"Unsupported template entry: {section}")
        _merge_table(root, (*path, name), value)


def _node_for_path(root: RenderNode, path: tuple[str, ...]) -> RenderNode:
    """Return or create the render node for a TOML path.

    Args:
        root: Root render node to traverse from.
        path: TOML table path to resolve.

    Returns:
        The render node for the requested path.
    """
    node = root
    for part in path:
        if part not in node.children:
            node.children[part] = RenderNode()
        node = node.children[part]
    return node


def _render_children(parent: RenderNode, level: int) -> list[str]:
    """Render all child nodes under a parent.

    Args:
        parent: Render node whose children should be rendered.
        level: Markdown heading level to use for direct children.

    Returns:
        Rendered markdown blocks for all descendants.
    """
    blocks: list[str] = []
    for name, node in parent.children.items():
        blocks.extend(_render_node(name, node, level))
    return blocks


def _render_node(name: str, node: RenderNode, level: int) -> list[str]:
    """Render one node and its descendants.

    Args:
        name: Markdown heading text.
        node: Render node containing body text and child sections.
        level: Markdown heading level for this node.

    Returns:
        Rendered markdown blocks for the node and descendants.
    """
    heading = f"{'#' * level} {name}"
    body = "\n\n".join(node.texts)
    block = f"{heading}\n{body}" if body else heading
    return [block, *_render_children(node, level + 1)]
