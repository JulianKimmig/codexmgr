"""Project-level codexmgr orchestration commands."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .apply_writes import write_project_state
from .copy_conflicts import (
    ConflictResolver,
    CopyConflict,
    CopyResolution,
    SourceUpdateReporter,
    choose_copy_resolutions,
    find_copy_conflicts,
)
from .copy_validation import (
    apply_source_updates,
    prepare_source_updates,
    skipped_copy_targets,
)
from .state import GeneratedFile, ProjectBuild
from .build import build_project_state, build_project_state_from_config
from .local_imports import prepare_local_import_state
from ..core.paths import config_path, project_codex_dir


@dataclass(frozen=True)
class PreparedProjectApply:
    """A project state whose copy conflicts have complete valid decisions.

    Attributes:
        state: Expected generated and copied project state.
        cwd: Project root used to normalize copy targets.
        conflicts: Discovery-time managed-copy conflict snapshots.
        resolutions: Complete actions keyed by normalized target path.
    """

    state: ProjectBuild
    cwd: Path
    conflicts: tuple[CopyConflict, ...]
    resolutions: Mapping[Path, CopyResolution]


def setup_project(cwd: Path) -> Path:
    """Create the project .codex directory and source config file.

    Args:
        cwd: Project directory to initialize.

    Returns:
        The created or existing .codex directory path. Existing source config
        content is preserved.
    """
    codex_dir = project_codex_dir(cwd)
    codex_dir.mkdir(parents=True, exist_ok=True)
    source_config = config_path(cwd)
    if not source_config.exists():
        source_config.write_text("", encoding="utf-8")
    return codex_dir


def apply_project_config(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    *,
    copy_resolutions: Mapping[Path, CopyResolution] | None = None,
    conflict_resolver: ConflictResolver | None = None,
    source_update_reporter: SourceUpdateReporter | None = None,
) -> None:
    """Apply project codexmgr configuration to generated Codex files.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named AGENTS.md sources.
        copy_resolutions: Explicit per-target resolutions for this invocation.
        conflict_resolver: Optional callback for unresolved copy conflicts.
        source_update_reporter: Optional warning callback before source writes.
    """
    apply_project_state(
        build_project_state(cwd, codex_home, codexmgr_home),
        cwd=cwd,
        copy_resolutions=copy_resolutions,
        conflict_resolver=conflict_resolver,
        source_update_reporter=source_update_reporter,
    )


def apply_project_state(
    state: ProjectBuild,
    *,
    cwd: Path | None = None,
    copy_resolutions: Mapping[Path, CopyResolution] | None = None,
    conflict_resolver: ConflictResolver | None = None,
    source_update_reporter: SourceUpdateReporter | None = None,
) -> None:
    """Apply a prebuilt project generated state.

    Args:
        state: Expected generated project state to write.
        cwd: Project root for relative resolution paths and display.
        copy_resolutions: Explicit per-target resolutions for this invocation.
        conflict_resolver: Optional callback for unresolved copy conflicts.
        source_update_reporter: Optional warning callback before source writes.
    """
    prepared = prepare_project_state_apply(
        state,
        cwd=cwd,
        copy_resolutions=copy_resolutions,
        conflict_resolver=conflict_resolver,
    )
    execute_prepared_project_apply(prepared, source_update_reporter)


def prepare_project_state_apply(
    state: ProjectBuild,
    *,
    cwd: Path | None = None,
    copy_resolutions: Mapping[Path, CopyResolution] | None = None,
    conflict_resolver: ConflictResolver | None = None,
) -> PreparedProjectApply:
    """Resolve and validate copy conflicts without writing any files.

    Args:
        state: Expected generated project state.
        cwd: Project root for relative resolution paths and display.
        copy_resolutions: Explicit per-target resolutions for this invocation.
        conflict_resolver: Optional callback for unresolved copy conflicts.

    Returns:
        Prepared project apply safe to execute with the captured decisions.
    """
    project_root = (cwd if cwd is not None else Path.cwd()).absolute()
    conflicts = sorted([*find_copy_conflicts(state.copy_files), *state.local_imports], key=lambda item: str(item.target))
    resolutions = choose_copy_resolutions(
        project_root,
        conflicts,
        copy_resolutions or {},
        conflict_resolver,
    )
    prepare_source_updates(project_root, conflicts, resolutions)
    return PreparedProjectApply(
        prepare_local_import_state(state, resolutions, project_root),
        project_root,
        tuple(conflicts),
        resolutions,
    )


def execute_prepared_project_apply(
    prepared: PreparedProjectApply,
    source_update_reporter: SourceUpdateReporter | None = None,
) -> None:
    """Recheck and execute a previously prepared project apply.

    Args:
        prepared: Project state and complete validated conflict decisions.
        source_update_reporter: Optional warning callback before source writes.
    """
    updates = prepare_source_updates(
        prepared.cwd,
        prepared.conflicts,
        prepared.resolutions,
    )
    apply_source_updates(updates, source_update_reporter)
    skipped_targets = skipped_copy_targets(prepared.cwd, prepared.resolutions)
    write_project_state(prepared.state, skipped_targets)


def build_project_files(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[GeneratedFile]:
    """Build expected generated file contents from project configuration.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named AGENTS.md sources.

    Returns:
        Expected generated files with their complete text content.
    """
    return build_project_state(cwd, codex_home, codexmgr_home).files
