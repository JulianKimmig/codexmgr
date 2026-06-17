"""Textual application for managing codexmgr project configuration."""

from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Label, SelectionList, Static

from ..core.errors import CommandError
from .diff import staged_diff_lines
from .items import agentsmd_items, hook_items, mcp_items, package_items, skill_items
from .models import ManagedItem
from .package_selection import set_package_selection
from .rendering import APP_CSS, SECTION_TITLES, TUI_BINDINGS, selection_for_item
from .state import StagedConfig, load_staged_config, save_staged_config


class CodexMgrTui(App[int]):
    """Interactive codexmgr project manager.

    Args:
        cwd: Project directory to manage.
        codex_home: Resolved Codex home directory.
        codexmgr_home: Resolved codexmgr home directory.
        no_sync: Whether Save should skip apply.
        show_diff: Whether the detail panel should include unified diffs.
    """

    CSS = APP_CSS

    BINDINGS = TUI_BINDINGS

    def __init__(
        self,
        *,
        cwd: Path,
        codex_home: Path,
        codexmgr_home: Path,
        no_sync: bool,
        show_diff: bool,
    ) -> None:
        """Initialize the TUI application.

        Args:
            cwd: Project directory to manage.
            codex_home: Resolved Codex home directory.
            codexmgr_home: Resolved codexmgr home directory.
            no_sync: Whether Save should skip apply.
            show_diff: Whether detail panels should include unified diffs.
        """
        super().__init__()
        self.cwd = cwd
        self.codex_home = codex_home
        self.codexmgr_home = codexmgr_home
        self.no_sync = no_sync
        self.show_diff = show_diff
        self.section = "dashboard"
        self.staged = load_staged_config(cwd, codex_home, codexmgr_home)
        self._selected_values: set[str] = set()
        self._refreshing = False
        self._status = "Ready"

    def compose(self) -> ComposeResult:
        """Compose Textual widgets.

        Returns:
            Textual compose result.
        """
        yield Header(show_clock=True)
        with Horizontal(id="layout"):
            with Vertical(id="nav"):
                yield Label("1 Dashboard")
                yield Label("2 AGENTS.md")
                yield Label("3 Skills")
                yield Label("4 Hooks")
                yield Label("5 Packages")
                yield Label("6 MCP")
                yield Label("")
                yield Label("space Toggle")
                yield Label("s Save")
                yield Label("r Refresh")
                yield Label("q Quit")
            with Vertical(id="main"):
                yield Static(id="title")
                yield SelectionList[str](id="items")
                yield Static(id="detail")
                yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Refresh the initial dashboard when the app mounts.

        Returns:
            None.
        """
        self._refresh_view()

    def action_section(self, section: str) -> None:
        """Switch to one management section.

        Args:
            section: Section identifier.
        """
        self.section = section
        self._refresh_view()

    def action_refresh(self) -> None:
        """Reload project config from disk.

        Returns:
            None.
        """
        self.staged = load_staged_config(self.cwd, self.codex_home, self.codexmgr_home)
        self._status = "Reloaded project configuration"
        self._refresh_view()

    def action_save(self) -> None:
        """Save staged changes and optionally apply project outputs.

        Returns:
            None.
        """
        try:
            messages = save_staged_config(self.staged, no_sync=self.no_sync)
            self.staged = load_staged_config(self.cwd, self.codex_home, self.codexmgr_home)
            self._status = " | ".join(messages)
        except CommandError as exc:
            self._status = f"ERROR {exc}"
        self._refresh_view()

    def action_quit(self) -> None:
        """Exit the TUI.

        Returns:
            None.
        """
        self.exit(0)

    @on(SelectionList.SelectedChanged, "#items")
    def _selection_changed(self, event: SelectionList.SelectedChanged[str]) -> None:
        """Apply selection changes to staged config.

        Args:
            event: Selection-list change event.
        """
        if self._refreshing:
            return
        selected = set(event.selection_list.selected)
        enabled = selected - self._selected_values
        disabled = self._selected_values - selected
        try:
            for value in sorted(enabled):
                self._set_selected(value, True)
            for value in sorted(disabled):
                self._set_selected(value, False)
            self._selected_values = selected
            self._status = "Staged changes pending" if self.staged.dirty() else "Ready"
        except CommandError as exc:
            self._status = f"ERROR {exc}"
            self._refresh_view()
            return
        self._refresh_status()

    def _set_selected(self, value: str, selected: bool) -> None:
        """Apply one selected state to the active section.

        Args:
            value: Item value from the selection list.
            selected: Whether the item is selected.
        """
        if self.section == "agentsmd":
            self.staged.set_agentsmd_enabled(value, selected)
        elif self.section == "skills":
            self.staged.set_skill_selected(value, selected)
        elif self.section == "hooks":
            self.staged.set_hook_selected(value, selected)
        elif self.section == "packages":
            set_package_selection(self.staged, value, selected)
        elif self.section == "mcp":
            self.staged.set_mcp_selected(value, selected)

    def _refresh_view(self) -> None:
        """Refresh title, selectable list, detail text, and status.

        Returns:
            None.
        """
        self._refreshing = True
        try:
            try:
                title = self.query_one("#title", Static)
                items = self.query_one("#items", SelectionList)
                detail = self.query_one("#detail", Static)
                status = self.query_one("#status", Static)
            except NoMatches:
                return
            title.update(self._title_text())
            rendered_items, warning = self._items_for_section()
            items.clear_options()
            items.add_options(selection_for_item(item) for item in rendered_items)
            if rendered_items:
                items.highlighted = 0
            self._selected_values = {item.selection_value() for item in rendered_items if item.state == "enabled"}
            detail.update(self._detail_text(rendered_items, warning))
            status.update(self._status_text())
            items.focus()
        finally:
            self._refreshing = False

    def _refresh_status(self) -> None:
        """Refresh low-cost dirty-state and status widgets only.

        Returns:
            None.
        """
        try:
            title = self.query_one("#title", Static)
            status = self.query_one("#status", Static)
        except NoMatches:
            return
        title.update(self._title_text())
        status.update(self._status_text())

    def _items_for_section(self) -> tuple[list[ManagedItem], str]:
        """Return display items for the active section.

        Returns:
            Display items and optional warning text.
        """
        if self.section == "agentsmd":
            return agentsmd_items(self.staged), ""
        if self.section == "skills":
            return skill_items(self.staged), ""
        if self.section == "hooks":
            return hook_items(self.staged), ""
        if self.section == "packages":
            return package_items(self.staged), ""
        if self.section == "mcp":
            return mcp_items(self.staged, discover=True)
        return [], ""

    def _title_text(self) -> Text:
        """Build the section title.

        Returns:
            Rich text title.
        """
        title = Text(SECTION_TITLES[self.section], style="bold white")
        if self.staged.dirty():
            title.append("  dirty", style="yellow")
        return title

    def _detail_text(self, items: list[ManagedItem], warning: str) -> Text:
        """Build detail panel content.

        Args:
            items: Items currently displayed.
            warning: Optional warning from item discovery.

        Returns:
            Rich text detail content.
        """
        if self.section == "dashboard":
            return Text(self._dashboard_detail())
        lines = [f"{len(items)} items"]
        if warning:
            lines.append(f"WARN {warning}")
        for item in items:
            if item.missing:
                lines.append(f"missing {item.name} {item.detail}".rstrip())
        return Text("\n".join(lines) if lines else "No items")

    def _dashboard_detail(self) -> str:
        """Build dashboard detail text.

        Returns:
            Dashboard detail text.
        """
        diff_text = staged_diff_lines(self.staged, show_diff=self.show_diff)
        return (
            f"Project: {self.cwd}\n"
            f"CODEX_HOME: {self.codex_home}\n"
            f"CODEXMGR_HOME: {self.codexmgr_home}\n"
            f"Sync: {diff_text}"
        )

    def _status_text(self) -> Text:
        """Build the footer status line.

        Returns:
            Rich text status.
        """
        style = "red" if self._status.startswith("ERROR ") else "green"
        return Text(self._status, style=style)
