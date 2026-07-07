"""Text builders for the Textual TUI panels."""

from pathlib import Path

from rich.text import Text

from .diff import staged_diff_lines
from .models import ManagedItem
from .rendering import SECTION_TITLES
from .state import StagedConfig


def title_text(section: str, *, dirty: bool) -> Text:
    """Build the active section title text.

    Args:
        section: Active section identifier.
        dirty: Whether staged configuration differs from disk.

    Returns:
        Rich title text.
    """
    title = Text(SECTION_TITLES[section], style="bold white")
    if dirty:
        title.append("  dirty", style="yellow")
    return title


def detail_text(
    section: str,
    items: list[ManagedItem],
    warning: str,
    staged: StagedConfig,
    *,
    show_diff: bool,
) -> Text:
    """Build the detail panel text for the active section.

    Args:
        section: Active section identifier.
        items: Items currently displayed by the active resource widget.
        warning: Optional warning from item discovery.
        staged: Staged project configuration.
        show_diff: Whether dashboard sync details should include unified diffs.

    Returns:
        Rich detail panel text.
    """
    if section == "dashboard":
        return Text(_dashboard_detail(staged, show_diff=show_diff))
    lines = [f"{len(items)} items"]
    if warning:
        lines.append(f"WARN {warning}")
    for item in items:
        if item.missing:
            lines.append(f"missing {item.name} {item.detail}".rstrip())
    return Text("\n".join(lines) if lines else "No items")


def status_text(status: str) -> Text:
    """Build the footer status line.

    Args:
        status: Current status message.

    Returns:
        Rich status text.
    """
    style = "red" if status.startswith("ERROR ") else "green"
    return Text(status, style=style)


def _dashboard_detail(staged: StagedConfig, *, show_diff: bool) -> str:
    """Build dashboard detail text.

    Args:
        staged: Staged project configuration.
        show_diff: Whether sync details should include unified diffs.

    Returns:
        Dashboard detail text.
    """
    return dashboard_detail(
        staged.cwd,
        staged.codex_home,
        staged.codexmgr_home,
        staged_diff_lines(staged, show_diff=show_diff),
    )


def dashboard_detail(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    sync_text: str,
) -> str:
    """Build dashboard detail text from resolved paths and sync state.

    Args:
        cwd: Project directory being managed.
        codex_home: Resolved Codex home directory.
        codexmgr_home: Resolved codexmgr home directory.
        sync_text: Generated-file sync summary or diff text.

    Returns:
        Dashboard detail text.
    """
    return (
        f"Project: {cwd}\n"
        f"CODEX_HOME: {codex_home}\n"
        f"CODEXMGR_HOME: {codexmgr_home}\n"
        f"Sync: {sync_text}"
    )
