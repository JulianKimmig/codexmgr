"""Save action mixin that coordinates TUI copy-conflict decisions."""

from pathlib import Path

from ..core.errors import CommandError
from ..project.copy_conflicts import CopyResolution
from .copy_conflicts import CopyConflictScreen
from .saving import save_staged_config, staged_copy_conflicts


class TuiSaveFlowMixin:
    """Provide the Textual save action and modal completion callback."""

    def action_save(self) -> None:
        """Save directly or pause for complete managed-copy resolutions.

        Returns:
            None.
        """
        try:
            conflicts = [] if self.no_sync else staged_copy_conflicts(self.staged)
        except CommandError as exc:
            self._status = f"ERROR {exc}"
            self._refresh_view()
            return
        if conflicts:
            self.push_screen(CopyConflictScreen(conflicts), self._finish_conflict_save)
            return
        self._save_with_resolutions({})

    def _finish_conflict_save(
        self,
        resolutions: dict[Path, CopyResolution] | None,
    ) -> None:
        """Continue save after the modal returns complete choices.

        Args:
            resolutions: Per-target choices, or ``None`` when aborted.
        """
        if resolutions is None:
            self._status = "Apply aborted; no files changed"
            self._refresh_view()
            return
        self._save_with_resolutions(resolutions)

    def _save_with_resolutions(
        self,
        resolutions: dict[Path, CopyResolution],
    ) -> None:
        """Persist staged state using already collected conflict choices.

        Args:
            resolutions: Complete per-target copy actions.
        """
        try:
            messages = save_staged_config(
                self.staged,
                no_sync=self.no_sync,
                copy_resolutions=resolutions,
            )
            self.staged = self._reload_staged_config()
            self._status = " | ".join(messages)
        except CommandError as exc:
            self._status = f"ERROR {exc}"
        self._refresh_view()

    def _reload_staged_config(self):
        """Reload staged state through the concrete app's configured homes.

        Returns:
            Fresh staged project configuration.
        """
        from .state import load_staged_config

        return load_staged_config(self.cwd, self.codex_home, self.codexmgr_home)
