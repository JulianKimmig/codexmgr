"""Rendering constants and helpers for the Textual TUI."""

from rich.text import Text
from textual.widgets.selection_list import Selection

from .models import ManagedItem

APP_CSS = """
Screen {
    background: #101418;
    color: #d8dee9;
}
#layout {
    height: 1fr;
}
#nav {
    width: 26;
    padding: 1;
    border: solid #3a4658;
}
#main {
    width: 1fr;
    padding: 1;
}
#title {
    height: 3;
    text-style: bold;
}
#items {
    height: 1fr;
    border: solid #3a4658;
    padding: 1;
}
#detail {
    height: 10;
    border: solid #3a4658;
    padding: 1;
}
#status {
    height: 3;
    color: #aeb8c4;
}
"""

SECTION_TITLES = {
    "dashboard": "Dashboard",
    "agentsmd": "AGENTS.md Templates",
    "skills": "Skills",
    "hooks": "Hooks",
    "packages": "Packages",
    "mcp": "MCP Servers",
}

TUI_BINDINGS = [
    ("1", "section('dashboard')", "Dashboard"),
    ("2", "section('agentsmd')", "AGENTS.md"),
    ("3", "section('skills')", "Skills"),
    ("4", "section('hooks')", "Hooks"),
    ("5", "section('packages')", "Packages"),
    ("6", "section('mcp')", "MCP"),
    ("r", "refresh", "Refresh"),
    ("s", "save", "Save"),
    ("q", "quit", "Quit"),
]

STATE_STYLES = {
    "enabled": "bold green",
    "disabled": "yellow",
    "available": "dim",
    "partial": "cyan",
    "configured": "blue",
    "error": "bold red",
}


def selection_for_item(item: ManagedItem) -> Selection[str]:
    """Convert a display item into a Textual selection.

    Args:
        item: Display item.

    Returns:
        Textual selection object.
    """
    label = Text(item.name)
    label.append("  ")
    label.append(item.state, style=STATE_STYLES.get(item.state, "white"))
    if item.missing:
        label.append("  missing", style="bold red")
    if item.detail:
        label.append(f"  {item.detail}", style="dim")
    return Selection(label, item.selection_value(), item.state == "enabled")
