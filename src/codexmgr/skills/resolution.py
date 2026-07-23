"""Resolve project skill configuration into generated state."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import _skill_lists
from .copies import (
    SkillCopy,
    obsolete_copy_targets,
    previous_skill_copies,
    validate_copy_targets,
)
from .selector import select_skill


@dataclass(frozen=True)
class SkillResolution:
    """Resolved skill configuration state.

    Attributes:
        entries: Generated Codex skills.config entries.
        copies: Managed project-local skill copies.
        obsolete_copy_targets: Previous managed copy targets to remove.
    """

    entries: list[dict[str, Any]]
    copies: list[SkillCopy]
    obsolete_copy_targets: list[Path]


def resolve_project_skills(
    project_config: Mapping[str, Any],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> SkillResolution:
    """Resolve configured skills into generated config and copy state.

    Args:
        project_config: Parsed project codexmgr config.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.
        previous_lock: Previous codexmgr lock data.

    Returns:
        Resolved skill state.
    """
    enabled_skills, disabled_skills = _skill_lists(project_config)
    previous_copies = previous_skill_copies(previous_lock, cwd, codexmgr_home)
    copies: list[SkillCopy] = []
    entries = [
        *_skill_entries(
            enabled_skills,
            cwd,
            codex_home,
            codexmgr_home,
            True,
            copies,
            previous_copies,
        ),
        *_skill_entries(
            disabled_skills,
            cwd,
            codex_home,
            codexmgr_home,
            False,
            copies,
            previous_copies,
        ),
    ]
    validate_copy_targets(copies, previous_lock, cwd, codexmgr_home)
    return SkillResolution(
        entries,
        copies,
        obsolete_copy_targets(previous_lock, copies, cwd, codexmgr_home),
    )


def _skill_entries(
    skills: list[str],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    enabled: bool,
    copies: list[SkillCopy],
    previous_copies: dict[str, SkillCopy],
) -> list[dict[str, Any]]:
    """Resolve a list of skills into generated entries.

    Args:
        skills: Skill references from project config.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.
        enabled: Desired enabled state.
        copies: Mutable copy list receiving managed copies.
        previous_copies: Previously managed copies rebound to this project.

    Returns:
        Generated Codex skills.config entries.
    """
    entries: list[dict[str, Any]] = []
    for skill in skills:
        selection = select_skill(
            skill,
            cwd,
            codex_home,
            codexmgr_home,
            enabled,
            previous_copies,
        )
        entries.append(selection.entry)
        if selection.copy is not None:
            copies.append(selection.copy)
    return entries
