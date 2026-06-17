"""Diff preview helpers for staged TUI configuration."""

from .state import StagedConfig
from ..project.sync import format_file_diffs, generated_file_diffs_from_config


def staged_diff_lines(staged: StagedConfig, *, show_diff: bool) -> str:
    """Build a staged generated-output diff preview.

    Args:
        staged: Staged project configuration to evaluate.
        show_diff: Whether to include unified diff text.

    Returns:
        Diff preview text. Empty text means generated files match staged state.
    """
    diffs = generated_file_diffs_from_config(
        staged.config,
        staged.cwd,
        staged.codex_home,
        staged.codexmgr_home,
    )
    if not diffs:
        return "Project Codex configuration is in sync\n"
    if show_diff:
        return format_file_diffs(diffs)
    return "".join(f"Out of sync: {diff.relative_path}\n" for diff in diffs)
