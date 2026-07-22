"""Helpers for preserving manual AGENTS.md content around a managed block."""

from pathlib import Path

from ..core.managed_text import render_managed_block

BEGIN_MARKER = "<!-- BEGIN CODEXMGR GENERATED -->"
END_MARKER = "<!-- END CODEXMGR GENERATED -->"


def write_managed_agents_md(path: Path, generated_markdown: str) -> None:
    """Write generated markdown into the CODEXMGR managed block.

    Args:
        path: Project AGENTS.md path to create or update.
        generated_markdown: Markdown content to place inside the managed block.

    Returns:
        None. The file is written with UTF-8 encoding.
    """
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = render_managed_agents_md(current, generated_markdown)
    path.write_text(updated, encoding="utf-8")


def render_managed_agents_md(current: str, generated_markdown: str) -> str:
    """Render AGENTS.md content with an updated managed block.

    Args:
        current: Existing AGENTS.md content, or an empty string for a new file.
        generated_markdown: Markdown content for the managed block.

    Returns:
        Full AGENTS.md content with the codexmgr managed block replaced or
        appended.
    """
    return render_managed_block(
        current,
        generated_markdown,
        begin_marker=BEGIN_MARKER,
        end_marker=END_MARKER,
        artifact_name="AGENTS.md",
    )
