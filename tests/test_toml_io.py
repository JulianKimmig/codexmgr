"""Tests for the minimal TOML reader and writer helpers."""

import pytest

from codexmgr.errors import CommandError
from codexmgr.toml_io import dump_toml


def test_dump_toml_rejects_nested_tables_inside_array_items():
    """Nested mappings in array-of-table entries fail instead of losing data."""
    data = {"items": [{"name": "one", "nested": {"value": "lost"}}]}

    with pytest.raises(
        CommandError,
        match="Unsupported nested table in TOML array item: items.nested",
    ):
        dump_toml(data)
