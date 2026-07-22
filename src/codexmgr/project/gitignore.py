"""Managed ignore rules for project-local Codex runtime state."""

from pathlib import Path

from .state import GeneratedFile
from ..core.managed_text import render_managed_block
from ..core.paths import codex_gitignore_path

BEGIN_MARKER = "# BEGIN CODEXMGR GENERATED"
END_MARKER = "# END CODEXMGR GENERATED"
MANAGED_IGNORE_RULES = """*
!/.gitignore
!/codexmgr.toml
!/codexmgr.lock
!/config.toml
!/hooks.json
!/agents/
!/agents/**
!/hooks/
!/hooks/**
__pycache__/
"""


def build_project_gitignore_file(cwd: Path) -> GeneratedFile:
    """Build the future-proof project Codex ignore-file state.

    Args:
        cwd: Project directory containing the local ``.codex`` home.

    Returns:
        Generated file preserving manual content outside codexmgr's block.
    """
    path = codex_gitignore_path(cwd)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    content = render_managed_block(
        current,
        MANAGED_IGNORE_RULES,
        begin_marker=BEGIN_MARKER,
        end_marker=END_MARKER,
        artifact_name=".codex/.gitignore",
    )
    return GeneratedFile(path, content)
