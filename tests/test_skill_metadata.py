"""Tests for reading declared names from Codex skill metadata."""

import pytest

from codexmgr.core.errors import CommandError
from codexmgr.skills.metadata import read_skill_name


def test_read_skill_name_returns_frontmatter_name(tmp_path):
    """Valid YAML frontmatter exposes the declared skill name."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: code-review\ndescription: Review code.\n---\n\n# Review\n",
        encoding="utf-8",
    )

    assert read_skill_name(skill_file) == "code-review"


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("# Missing\n", "missing YAML frontmatter"),
        ("---\nname: [broken\n---\n", "invalid YAML frontmatter"),
        ("---\ndescription: Missing name.\n---\n", "name must be a non-empty string"),
        ("---\nname: '   '\n---\n", "name must be a non-empty string"),
    ],
)
def test_read_skill_name_rejects_invalid_metadata(tmp_path, content, message):
    """Malformed or incomplete frontmatter fails with a focused error."""
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")

    with pytest.raises(CommandError, match=message):
        read_skill_name(skill_file)
