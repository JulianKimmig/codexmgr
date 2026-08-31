"""Textual application for managing codexmgr project configuration."""

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Label, SelectionList, Static, Tree

from ..core.errors import CommandError
from .focus import (
    highlighted_list_item,
    highlighted_rule_item,
    restore_rule_tree_focus,
    restore_selection_list_focus,
)
from .models import ManagedItem
from .panels import detail_text, status_text, title_text
from .rendering import APP_CSS, NAV_LABELS, TUI_BINDINGS, selection_for_item
from .rule_tree import populate_rule_tree
from .sections import cycle_section_state, items_for_section, set_section_selected
from .save_flow import TuiSaveFlowMixin
from .state import StagedConfig, load_staged_config


class CodexMgrTui(TuiSaveFlowMixin, App[int]):
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
        self._rendered_items: list[ManagedItem] = []
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
                for label in NAV_LABELS:
                    yield Label(label)
            with Vertical(id="main"):
                yield Static(id="title")
                yield SelectionList[str](id="items")
                yield Tree("Rules", id="rule-tree")
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

    def action_quit(self) -> None:
        """Exit the TUI.

        Returns:
            None.
        """
        self.exit(0)

    def action_cycle_state(self) -> None:
        """Cycle the highlighted row through its available states.

        Returns:
            None.
        """
        try:
            if self.section == "rules":
                item = highlighted_rule_item(self.query_one("#rule-tree", Tree))
            else:
                item = highlighted_list_item(
                    self.query_one("#items", SelectionList),
                    self._rendered_items,
                )
        except NoMatches:
            return
        if item is None:
            return
        selection_value = item.selection_value()
        try:
            cycle_section_state(self.staged, self.section, item)
            self._status = "Staged changes pending" if self.staged.dirty() else "Ready"
        except CommandError as exc:
            self._status = f"ERROR {exc}"
        self._refresh_view(selection_value)

    @on(SelectionList.SelectedChanged, "#items")
    def _selection_changed(self, event: SelectionList.SelectedChanged[str]) -> None:
        """Apply selection changes to staged config.

        Args:
            event: Selection-list change event.
        """
        if self._refreshing:
            return
        if self.section == "rules":
            return
        selected = set(event.selection_list.selected)
        enabled = selected - self._selected_values
        disabled = self._selected_values - selected
        try:
            for value in sorted(enabled):
                set_section_selected(self.staged, self.section, value, True)
            for value in sorted(disabled):
                set_section_selected(self.staged, self.section, value, False)
            self._selected_values = selected
            self._status = "Staged changes pending" if self.staged.dirty() else "Ready"
        except CommandError as exc:
            self._status = f"ERROR {exc}"
            self._refresh_view()
            return
        self._refresh_status()

    def _refresh_view(self, selection_value: str | None = None) -> None:
        """Refresh title, selectable list, detail text, and status.

        Args:
            selection_value: Optional stable item value to keep highlighted.

        Returns:
            None.
        """
        self._refreshing = True
        try:
            try:
                title = self.query_one("#title", Static)
                items = self.query_one("#items", SelectionList)
                rule_tree = self.query_one("#rule-tree", Tree)
                detail = self.query_one("#detail", Static)
                status = self.query_one("#status", Static)
            except NoMatches:
                return
            title.update(title_text(self.section, dirty=self.staged.dirty()))
            rendered_items, warning = self._refresh_resource_widget(
                items,
                rule_tree,
                selection_value,
            )
            detail.update(
                detail_text(
                    self.section,
                    rendered_items,
                    warning,
                    self.staged,
                    show_diff=self.show_diff,
                ),
            )
            status.update(status_text(self._status))
        finally:
            self._refreshing = False

    def _refresh_resource_widget(
        self,
        items: SelectionList[str],
        rule_tree: Tree[ManagedItem | None],
        selection_value: str | None,
    ) -> tuple[list[ManagedItem], str]:
        """Refresh the active resource widget.

        Args:
            items: Selection list widget used by non-rule sections.
            rule_tree: Tree widget used by the rules section.
            selection_value: Optional stable item value to keep highlighted.

        Returns:
            Rendered items and optional warning text.
        """
        if self.section == "rules":
            items.display = False
            rule_tree.display = True
            rendered_items = populate_rule_tree(rule_tree, self.staged)
            self._rendered_items = rendered_items
            self._selected_values = set()
            restore_rule_tree_focus(rule_tree, selection_value)
            rule_tree.focus()
            return rendered_items, ""
        rule_tree.display = False
        items.display = True
        rendered_items, warning = items_for_section(self.staged, self.section)
        self._rendered_items = rendered_items
        items.clear_options()
        items.add_options(selection_for_item(item) for item in rendered_items)
        restore_selection_list_focus(items, selection_value)
        self._selected_values = {
            item.selection_value()
            for item in rendered_items
            if item.state == "enabled"
        }
        items.focus()
        return rendered_items, warning

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
        title.update(title_text(self.section, dirty=self.staged.dirty()))
        status.update(status_text(self._status))
