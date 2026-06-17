"""Resolve project skill configuration into generated state."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import _skill_lists
from .copies import (
    SkillCopy,
    obsolete_copy_targets,
    validate_copy_targets,
)
from .sources import (
    CODEXMGR_HOME_SOURCE,
    SkillSource,
    project_skill_dir,
    resolve_skill_reference,
)


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
    copies: list[SkillCopy] = []
    entries = [
        *_skill_entries(enabled_skills, cwd, codex_home, codexmgr_home, True, copies),
        *_skill_entries(disabled_skills, cwd, codex_home, codexmgr_home, False, copies),
    ]
    validate_copy_targets(copies, previous_lock)
    return SkillResolution(
        entries,
        copies,
        obsolete_copy_targets(previous_lock, copies),
    )


def _skill_entries(
    skills: list[str],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    enabled: bool,
    copies: list[SkillCopy],
) -> list[dict[str, Any]]:
    """Resolve a list of skills into generated entries.

    Args:
        skills: Skill references from project config.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.
        enabled: Desired enabled state.
        copies: Mutable copy list receiving managed copies.

    Returns:
        Generated Codex skills.config entries.
    """
    return [
        _skill_entry(skill, cwd, codex_home, codexmgr_home, enabled, copies)
        for skill in skills
    ]


def _skill_entry(
    skill: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    enabled: bool,
    copies: list[SkillCopy],
) -> dict[str, Any]:
    """Resolve one skill into a generated config entry.

    Args:
        skill: Skill reference from project config.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.
        enabled: Desired enabled state.
        copies: Mutable copy list receiving managed copies.

    Returns:
        Generated Codex skills.config entry.
    """
    source = resolve_skill_reference(skill, cwd, codex_home, codexmgr_home)
    if source is None:
        return {"name": skill, "enabled": enabled}
    if source.source_type == CODEXMGR_HOME_SOURCE:
        return _codexmgr_home_entry(source, cwd, enabled, copies)
    return {"path": str(source.skill_file), "enabled": enabled}


def _codexmgr_home_entry(
    source: SkillSource,
    cwd: Path,
    enabled: bool,
    copies: list[SkillCopy],
) -> dict[str, Any]:
    """Build a generated entry for a codexmgr-home skill.

    Args:
        source: Resolved codexmgr-home skill source.
        cwd: Project directory.
        enabled: Desired enabled state.
        copies: Mutable copy list receiving managed copies.

    Returns:
        Generated Codex skills.config entry.
    """
    if not enabled:
        return {"name": source.name, "enabled": False}
    target = project_skill_dir(cwd, source.name)
    copies.append(SkillCopy(source.name, source.skill_dir, target))
    return {"path": str((target / "SKILL.md").resolve()), "enabled": True}
