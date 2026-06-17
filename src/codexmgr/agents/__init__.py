"""AGENTS.md template resolution, rendering, and managed-file helpers."""

from .file import render_managed_agents_md, write_managed_agents_md
from .manager import (
    add_agentsmd,
    init_agentsmd_template,
    list_agentsmd_options,
    remove_agentsmd,
    resolve_locked_agents_md,
    show_agentsmd,
    validate_agentsmd,
    write_agents_md,
)
from .renderer import RenderNode, render_agents_markdown

__all__ = [
    "RenderNode",
    "add_agentsmd",
    "init_agentsmd_template",
    "list_agentsmd_options",
    "remove_agentsmd",
    "render_agents_markdown",
    "render_managed_agents_md",
    "resolve_locked_agents_md",
    "show_agentsmd",
    "validate_agentsmd",
    "write_agents_md",
    "write_managed_agents_md",
]
