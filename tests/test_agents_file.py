from pathlib import Path

import pytest

from codexmgr.agents_file import write_managed_agents_md
from codexmgr.errors import CommandError

BEGIN = "<!-- BEGIN CODEXMGR GENERATED -->"
END = "<!-- END CODEXMGR GENERATED -->"


@pytest.fixture
def agents_md_path(tmp_path: Path) -> Path:
    return tmp_path / "AGENTS.md"


def test_creates_missing_agents_file_with_generated_block(agents_md_path: Path):
    write_managed_agents_md(agents_md_path, "# rules\nhello\n")

    assert agents_md_path.read_text(encoding="utf-8") == (
        f"{BEGIN}\n# rules\nhello\n{END}\n"
    )


def test_appends_generated_block_to_existing_agents_file(agents_md_path: Path):
    agents_md_path.write_text("# Manual\nkeep this\n", encoding="utf-8")

    write_managed_agents_md(agents_md_path, "# Generated\nnew\n")

    assert agents_md_path.read_text(encoding="utf-8") == (
        f"# Manual\nkeep this\n\n{BEGIN}\n# Generated\nnew\n{END}\n"
    )


def test_replaces_existing_generated_block_content(agents_md_path: Path):
    agents_md_path.write_text(
        f"# Manual\n\n{BEGIN}\nold\n{END}\n\n# Tail\n",
        encoding="utf-8",
    )

    write_managed_agents_md(agents_md_path, "# Generated\nnew\n")

    assert agents_md_path.read_text(encoding="utf-8") == (
        f"# Manual\n\n{BEGIN}\n# Generated\nnew\n{END}\n\n# Tail\n"
    )


def test_rejects_incomplete_generated_block(agents_md_path: Path):
    agents_md_path.write_text(f"# Manual\n\n{BEGIN}\nold\n", encoding="utf-8")

    with pytest.raises(CommandError):
        write_managed_agents_md(agents_md_path, "# Generated\nnew\n")
