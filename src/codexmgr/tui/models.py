"""Data models used by the interactive codexmgr interface."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ManagedItem:
    """One selectable resource in the TUI.

    Attributes:
        name: User-facing resource name or reference.
        state: Current state label such as enabled, disabled, or available.
        missing: Whether the configured resource cannot currently be resolved.
        detail: Optional extra context for display.
        value: Optional stable selection value, used when the display label is
            not sufficient to identify the selected resource.
    """

    name: str
    state: str
    missing: bool = False
    detail: str = ""
    value: str = ""

    def selection_value(self) -> str:
        """Return the stable value used by selection widgets.

        Returns:
            Explicit value when configured, otherwise the display name.
        """
        return self.value or self.name


@dataclass(frozen=True)
class DashboardSummary:
    """Compact project state summary for the dashboard.

    Attributes:
        project: Project directory display path.
        codex_home: Resolved Codex home display path.
        codexmgr_home: Resolved codexmgr home display path.
        dirty: Whether staged changes differ from the file on disk.
        diff_count: Number of generated outputs that differ from staged state.
    """

    project: str
    codex_home: str
    codexmgr_home: str
    dirty: bool
    diff_count: int
