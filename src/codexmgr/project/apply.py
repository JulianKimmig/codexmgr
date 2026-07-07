"""Project-level codexmgr orchestration commands."""

from collections.abc import Mapping
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
from .resolution import resolve_project_components
from .state import GeneratedFile, ProjectBuild
from ..core.paths import config_path, lock_path, project_codex_dir
from ..core.toml_io import load_optional_toml_file
from ..custom_agents.copies import (
    apply_agent_copy,
    remove_agent_copy_target,
)
from ..rules.copies import apply_rule_copy, remove_rule_copy_target
from ..skills.copies import (
    apply_skill_copy,
    expected_copy_files,
    remove_skill_copy_target,
)
from ..hooks.copies import apply_hook_copy, remove_hook_copy_target


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
    apply_project_state(build_project_state(cwd, codex_home, codexmgr_home))


def apply_project_state(state: ProjectBuild) -> None:
    """Apply a prebuilt project generated state.

    Args:
        state: Expected generated project state to write.
    """
    for target in state.obsolete_skill_copy_targets:
        remove_skill_copy_target(target)
    for target in state.obsolete_hook_copy_targets:
        remove_hook_copy_target(target)
    for target in state.obsolete_agent_copy_targets:
        remove_agent_copy_target(target)
    for target in state.obsolete_rule_copy_targets:
        remove_rule_copy_target(target)
    for target in state.obsolete_file_targets:
        remove_file_target(target)
    for skill_copy in state.skill_copies:
        apply_skill_copy(skill_copy)
    for hook_copy in state.hook_copies:
        apply_hook_copy(hook_copy)
    for agent_copy in state.agent_copies:
        apply_agent_copy(agent_copy)
    for rule_copy in state.rule_copies:
        apply_rule_copy(rule_copy)
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
    )
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
