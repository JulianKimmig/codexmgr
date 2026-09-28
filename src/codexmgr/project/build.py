"""Build expected project outputs, copy ownership, and pending local imports."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..core.paths import lock_path
from ..core.toml_io import load_optional_toml_file
from ..skills.copies import expected_copy_files
from .config import load_required_project_config
from .generated import (
    build_codex_config, build_generated_files, build_lock_data, obsolete_generated_files,
)
from .local_discovery import discover_local_imports, project_only_refs
from .resolution import resolve_project_components
from .state import ProjectBuild


def build_project_state(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> ProjectBuild:
    """Build expected generated project state from configuration.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named sources.

    Returns:
        Expected generated project state.
    """
    config = load_required_project_config(cwd)
    return build_project_state_from_config(config, cwd, codex_home, codexmgr_home)


def build_project_state_from_config(
    config: Mapping[str, Any],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> ProjectBuild:
    """Build expected generated state from an in-memory project config.

    Args:
        config: Parsed codexmgr configuration to evaluate.
        cwd: Project directory whose generated files should be checked.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named sources.

    Returns:
        Expected generated project state for the supplied configuration.
    """
    previous_lock = load_optional_toml_file(lock_path(cwd))
    resolution = resolve_project_components(
        config,
        cwd,
        codex_home,
        codexmgr_home,
        previous_lock,
    )
    codex_config = build_codex_config(
        cwd,
        config,
        resolution.skills.entries,
        resolution.mcp,
        previous_lock,
    )
    lock_data = build_lock_data(
        config,
        resolution.locked_agents_md,
        resolution.agents,
        resolution.skills,
        resolution.hooks,
        resolution.rules,
        resolution.mcp,
        resolution.guides,
    )
    for family in ("guides", "rules"):
        if family in config:
            remembered = project_only_refs(previous_lock, family)
            if remembered:
                lock_data[family]["project_only"] = remembered
    local_imports = discover_local_imports(config, previous_lock, cwd, codexmgr_home)
    files = build_generated_files(
        cwd,
        config,
        resolution.locked_agents_md,
        resolution.hooks,
        lock_data,
        codex_config,
    )
    return ProjectBuild(
        files,
        [
            *expected_copy_files(resolution.skills.copies),
            *resolution.hooks.copy_files,
            *resolution.agents.copy_files,
            *resolution.rules.copy_files,
            *resolution.guides.copy_files,
        ],
        resolution.skills.copies,
        resolution.skills.obsolete_copy_targets,
        resolution.hooks.copies,
        resolution.hooks.obsolete_copy_targets,
        resolution.agents.copies,
        resolution.agents.obsolete_copy_targets,
        resolution.rules.copies,
        resolution.rules.obsolete_copy_targets,
        obsolete_generated_files(cwd, resolution.hooks),
        resolution.guides.copies,
        resolution.guides.obsolete_copy_targets,
        cwd / ".guides",
        local_imports,
    )
