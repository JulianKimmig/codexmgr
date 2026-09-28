"""Guide-specific staged operations shared by tree and checkbox dispatch."""

from ..guides.config import remove_guide, set_guide_state_in_config


class GuideStageMixin:
    """Guide selection operations on the roots and configuration of StagedConfig."""

    def set_guide_enabled(self, guide: str, enabled: bool) -> None:
        """Set a document or folder selector without expanding its descendants.

        Args:
            guide: Exact store-relative document or folder reference.
            enabled: Whether to include the selector or explicitly exclude it.
        """
        set_guide_state_in_config(self.config, guide, self.codexmgr_home, enabled=enabled)

    def set_guide_selected(self, guide: str, selected: bool) -> None:
        """Apply checkbox semantics while preserving previously owned exclusions.

        Args:
            guide: Canonical guide reference being selected.
            selected: Whether the selector should be enabled.
        """
        if selected or guide in self.original_guides:
            self.set_guide_enabled(guide, selected)
        else:
            remove_guide(self.config, guide, self.codexmgr_home)
