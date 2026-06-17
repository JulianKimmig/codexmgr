"""Tests for the minimal TOML reader and writer helpers."""

import pytest

from codexmgr.core.errors import CommandError
from codexmgr.core.toml_io import dump_toml


def test_dump_toml_preserves_empty_nested_tables():
    """Empty nested mappings are emitted as explicit TOML tables."""
    data = {"mcp": {"servers": {"browsermcp": {"env_http_headers": {}}}}}

    assert dump_toml(data) == "[mcp.servers.browsermcp.env_http_headers]\n"


def test_dump_toml_rejects_nested_tables_inside_array_items():
    """Nested mappings in array-of-table entries fail instead of losing data."""
    data = {"items": [{"name": "one", "nested": {"value": "lost"}}]}

    with pytest.raises(
        CommandError,
        match="Unsupported nested table in TOML array item: items.nested",
    ):
        dump_toml(data)
