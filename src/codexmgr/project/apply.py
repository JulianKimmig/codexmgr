"""Project-level codexmgr orchestration commands."""

from pathlib import Path
from typing import Any

from .config import load_required_project_config
from .generated import (
    build_codex_config,
    build_generated_files,
    build_lock_data,
    obsolete_generated_files,
    remove_file_target,
)
from .state import GeneratedFile, ProjectBuild
from ..agents.manager import resolve_locked_agents_md
from ..core.paths import config_path, lock_path, project_codex_dir
from ..core.toml_io import load_optional_toml_file
from ..mcp.config import resolve_overrides
from ..skills.copies import (
    apply_skill_copy,
    expected_copy_files,
    remove_skill_copy_target,
)
from ..skills.resolution import SkillResolution, resolve_project_skills
from ..hooks.copies import apply_hook_copy, remove_hook_copy_target
from ..hooks.resolution import (
    HookResolution,
    empty_hook_resolution,
    resolve_project_hooks,
)


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


def apply_project_config(cwd: Path, codex_home: Path, codexmgr_home: Path) -> None:
    """Apply project codexmgr configuration to generated Codex files.

    Args:
        cwd: Project directory whose .codex/codexmgr.toml should be applied.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve named AGENTS.md sources.
    """
    state = build_project_state(cwd, codex_home, codexmgr_home)
    for target in state.obsolete_skill_copy_targets:
        remove_skill_copy_target(target)
    for target in state.obsolete_hook_copy_targets:
        remove_hook_copy_target(target)
    for target in state.obsolete_file_targets:
        remove_file_target(target)
    for skill_copy in state.skill_copies:
        apply_skill_copy(skill_copy)
    for hook_copy in state.hook_copies:
        apply_hook_copy(hook_copy)
    for generated_file in state.files:
        generated_file.path.parent.mkdir(parents=True, exist_ok=True)
        generated_file.path.write_text(generated_file.content, encoding="utf-8")


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
    previous_lock = load_optional_toml_file(lock_path(cwd))
    locked_agents_md = resolve_locked_agents_md(config, cwd, codexmgr_home)
    skill_resolution = _resolve_skills(config, cwd, codex_home, codexmgr_home, previous_lock)
    hook_resolution = _resolve_hooks(config, cwd, codexmgr_home, previous_lock)
    mcp_overrides = resolve_overrides(config, strict=True)
    codex_config = build_codex_config(
        cwd,
        config,
        skill_resolution.entries,
        mcp_overrides,
        previous_lock,
    )
    lock_data = build_lock_data(
        config,
        locked_agents_md,
        skill_resolution,
        hook_resolution,
        mcp_overrides,
    )
    files = build_generated_files(
        cwd,
        config,
        locked_agents_md,
        hook_resolution,
        lock_data,
        codex_config,
    )
    return ProjectBuild(
        files,
        [*expected_copy_files(skill_resolution.copies), *hook_resolution.copy_files],
        skill_resolution.copies,
        skill_resolution.obsolete_copy_targets,
        hook_resolution.copies,
        hook_resolution.obsolete_copy_targets,
        obsolete_generated_files(cwd, hook_resolution),
    )


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


def _resolve_skills(
    config: dict[str, Any],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    previous_lock: dict[str, Any],
) -> SkillResolution:
    """Resolve skills only when the project config owns the skills table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved skill state.
    """
    if "skills" not in config:
        return SkillResolution([], [], [])
    return resolve_project_skills(config, cwd, codex_home, codexmgr_home, previous_lock)


def _resolve_hooks(
    config: dict[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: dict[str, Any],
) -> HookResolution:
    """Resolve hooks only when the project config owns the hooks table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codexmgr_home: codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved hook state.
    """
    if "hooks" not in config:
        return empty_hook_resolution()
    return resolve_project_hooks(config, cwd, codexmgr_home, previous_lock)
