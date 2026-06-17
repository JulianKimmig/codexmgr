"""Tests for rendering AGENTS.md template TOML into markdown."""

import pytest

from codexmgr.agents.renderer import render_agents_markdown
from codexmgr.core.errors import CommandError


def test_renderer_rejects_scalar_top_level_template_entries():
    """Scalar top-level entries fail instead of being silently ignored."""
    sources = {"template": {"rules": "plain text"}}

    with pytest.raises(CommandError, match="Template section must be a table: rules"):
        render_agents_markdown(sources)


def test_renderer_rejects_unsupported_nested_template_entries():
    """Nested entries other than text strings and child tables fail loudly."""
    sources = {"template": {"rules": {"priority": 1}}}

    with pytest.raises(CommandError, match="Unsupported template entry: rules.priority"):
        render_agents_markdown(sources)


def test_renderer_rejects_non_table_source_entries():
    """Each locked AGENTS.md source must be represented as a TOML table."""
    sources = {"template": "not a table"}

    with pytest.raises(CommandError, match="Source entries must be TOML tables"):
        render_agents_markdown(sources)
