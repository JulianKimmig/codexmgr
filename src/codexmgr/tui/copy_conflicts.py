"""Modal TUI screen for per-target managed-copy conflict choices."""

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ..project.copy_conflicts import CopyConflict, CopyResolution


class CopyConflictScreen(ModalScreen[dict[Path, CopyResolution] | None]):
    """Collect one non-persistent action for every managed-copy conflict.

    Args:
        conflicts: Source-backed target conflicts to present in stable order.
    """

    CSS = """
    CopyConflictScreen {
        align: center middle;
        background: $background 70%;
    }
    #copy-conflict-dialog {
        width: 90%;
        max-width: 110;
        height: auto;
        padding: 1 2;
        border: thick $warning;
        background: $surface;
    }
    #copy-conflict-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #copy-conflict-buttons {
        height: auto;
        margin-top: 1;
    }
    #copy-conflict-buttons Button {
        margin-right: 1;
    }
    """

    BINDINGS = [
        Binding("k", "choose('keep-local')", "Keep local", priority=True),
        Binding("o", "choose('overwrite-local')", "Overwrite local", priority=True),
        Binding("u", "choose('update-source')", "Update source", priority=True),
        Binding("a", "abort", "Abort", priority=True),
        Binding("escape", "abort", "Abort", priority=True),
    ]

    def __init__(self, conflicts: list[CopyConflict]) -> None:
        """Initialize the conflict queue.

        Args:
            conflicts: Conflicts requiring a decision before save.
        """
        super().__init__()
        self.conflicts = conflicts
        self.index = 0
        self.resolutions: dict[Path, CopyResolution] = {}

    def compose(self) -> ComposeResult:
        """Compose conflict provenance and four action buttons.

        Returns:
            Textual compose result.
        """
        with Vertical(id="copy-conflict-dialog"):
            yield Label("Managed copy conflict", id="copy-conflict-title")
            yield Static(id="copy-conflict-detail")
            with Horizontal(id="copy-conflict-buttons"):
                yield Button("Keep local [k]", id="keep-local")
                yield Button("Overwrite local [o]", id="overwrite-local")
                yield Button("Update shared source [u]", id="update-source")
                yield Button("Abort [a]", id="abort", variant="error")

    def on_mount(self) -> None:
        """Render the first queued conflict.

        Returns:
            None.
        """
        self._refresh_conflict()

    def action_choose(self, action: str) -> None:
        """Record one action and advance or dismiss the modal.

        Args:
            action: Copy-resolution string from a binding or button.
        """
        conflict = self.conflicts[self.index]
        self.resolutions[conflict.target.absolute()] = CopyResolution(action)
        self.index += 1
        if self.index == len(self.conflicts):
            self.dismiss(dict(self.resolutions))
            return
        self._refresh_conflict()

    def action_abort(self) -> None:
        """Dismiss without resolutions so the caller performs no save.

        Returns:
            None.
        """
        self.dismiss(None)

    @on(Button.Pressed)
    def _button_pressed(self, event: Button.Pressed) -> None:
        """Translate a modal button press into a conflict action.

        Args:
            event: Pressed button event.
        """
        if event.button.id == "abort":
            self.action_abort()
            return
        if event.button.id is not None:
            self.action_choose(event.button.id)

    def _refresh_conflict(self) -> None:
        """Render provenance for the current conflict.

        Returns:
            None.
        """
        conflict = self.conflicts[self.index]
        self.query_one("#copy-conflict-detail", Static).update(
            f"Conflict {self.index + 1} of {len(self.conflicts)}\n"
            f"Target: {conflict.target}\n"
            f"Source: {conflict.source}\n\n"
            "Keep local applies only to this save. Updating the source may "
            "affect every project that uses this shared resource.",
        )
