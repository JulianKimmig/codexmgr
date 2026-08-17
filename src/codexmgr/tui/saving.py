"""Transactional staged-config save helpers for the Textual interface."""

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.paths import config_path
from ..core.toml_io import dump_toml, write_toml_file
from ..project.apply import (
    build_project_state_from_config,
    execute_prepared_project_apply,
    prepare_project_state_apply,
)
from ..project.copy_conflicts import (
    CopyConflict,
    CopyResolution,
    find_copy_conflicts,
)

if TYPE_CHECKING:
    from .state import StagedConfig


def staged_copy_conflicts(staged: "StagedConfig") -> list[CopyConflict]:
    """Discover copy conflicts for the current in-memory staged config.

    Args:
        staged: TUI project configuration staged in memory.

    Returns:
        Source-backed target conflicts requiring TUI choices.
    """
    state = build_project_state_from_config(
        staged.config,
        staged.cwd,
        staged.codex_home,
        staged.codexmgr_home,
    )
    return find_copy_conflicts(state.copy_files)


def save_staged_config(
    staged: "StagedConfig",
    *,
    no_sync: bool,
    copy_resolutions: Mapping[Path, CopyResolution] | None = None,
) -> list[str]:
    """Preflight conflicts, save staged config, and apply project outputs.

    Args:
        staged: Staged project configuration to persist.
        no_sync: Whether to skip apply after writing codexmgr.toml.
        copy_resolutions: Complete TUI choices for current copy conflicts.

    Returns:
        User-facing status messages.
    """
    prepared = None
    if not no_sync:
        state = build_project_state_from_config(
            staged.config,
            staged.cwd,
            staged.codex_home,
            staged.codexmgr_home,
        )
        prepared = prepare_project_state_apply(
            state,
            cwd=staged.cwd,
            copy_resolutions=copy_resolutions,
        )
    write_toml_file(config_path(staged.cwd), staged.config)
    messages = ["Saved project configuration"]
    if prepared is not None:
        updated_sources: list[Path] = []
        execute_prepared_project_apply(
            prepared,
            lambda conflict: updated_sources.append(conflict.source),
        )
        messages.extend(f"Updated shared source {path}" for path in updated_sources)
        messages.append("Applied project Codex configuration")
    staged.original_text = dump_toml(staged.config)
    return messages
