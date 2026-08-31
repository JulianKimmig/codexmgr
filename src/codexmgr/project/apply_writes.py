"""Filesystem writes for an already-prepared project apply."""

from pathlib import Path

from ..custom_agents.copies import apply_agent_copy, remove_agent_copy_target
from ..hooks.copies import apply_hook_copy, remove_hook_copy_target
from ..rules.copies import apply_rule_copy, remove_rule_copy_target
from ..skills.copies import apply_skill_copy, remove_skill_copy_target
from .generated import remove_file_target
from .state import ProjectBuild


def write_project_state(state: ProjectBuild, skipped_targets: set[Path]) -> None:
    """Write a project state after copy conflicts have been resolved.

    Args:
        state: Expected generated project state.
        skipped_targets: Managed copy targets preserved for this invocation.
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
        apply_skill_copy(skill_copy, skipped_targets)
    for hook_copy in state.hook_copies:
        apply_hook_copy(hook_copy, skipped_targets)
    for agent_copy in state.agent_copies:
        apply_agent_copy(agent_copy, skipped_targets)
    for rule_copy in state.rule_copies:
        apply_rule_copy(rule_copy, skipped_targets)
    for generated_file in state.files:
        generated_file.path.parent.mkdir(parents=True, exist_ok=True)
        generated_file.path.write_text(generated_file.content, encoding="utf-8")
