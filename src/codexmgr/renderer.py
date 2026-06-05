from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .errors import CommandError


@dataclass
class RenderNode:
    texts: list[str] = field(default_factory=list)
    children: OrderedDict[str, "RenderNode"] = field(default_factory=OrderedDict)


def render_agents_markdown(sources: Mapping[str, Any]) -> str:
    root = RenderNode()

    for source_data in sources.values():
        if not isinstance(source_data, Mapping):
            raise CommandError("Source entries must be TOML tables")
        _merge_source(root, source_data)

    blocks = _render_children(root, 1)
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _merge_source(parent: RenderNode, source_data: Mapping[str, Any]) -> None:
    for name, value in source_data.items():
        if isinstance(value, Mapping):
            _merge_table(parent, (name,), value)


def _merge_table(root: RenderNode, path: tuple[str, ...], table: Mapping[str, Any]) -> None:
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
        if isinstance(value, Mapping):
            _merge_table(root, (*path, name), value)


def _node_for_path(root: RenderNode, path: tuple[str, ...]) -> RenderNode:
    node = root
    for part in path:
        if part not in node.children:
            node.children[part] = RenderNode()
        node = node.children[part]
    return node


def _render_children(parent: RenderNode, level: int) -> list[str]:
    blocks: list[str] = []
    for name, node in parent.children.items():
        blocks.extend(_render_node(name, node, level))
    return blocks


def _render_node(name: str, node: RenderNode, level: int) -> list[str]:
    heading = f"{'#' * level} {name}"
    body = "\n\n".join(node.texts)
    block = f"{heading}\n{body}" if body else heading
    return [block, *_render_children(node, level + 1)]
