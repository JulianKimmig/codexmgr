"""Select portable Codex config entries for resolved project skills."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from .candidates import all_named_skill_sources, skill_reference_candidates
from .copies import SkillCopy
from .metadata import read_skill_name, try_read_skill_name
from .sources import (
    CODEX_HOME_SOURCE,
    CODEXMGR_HOME_SOURCE,
    LOCAL_SOURCE,
    PATH_SOURCE,
    SkillSource,
    is_named_skill,
    project_skill_dir,
)

_SOURCE_LABELS = {
    CODEXMGR_HOME_SOURCE: "codexmgr_home",
    CODEX_HOME_SOURCE: "codex_home",
    LOCAL_SOURCE: "project",
    PATH_SOURCE: "path",
}
_SOURCE_RANKS = {
    CODEXMGR_HOME_SOURCE: 1,
    CODEX_HOME_SOURCE: 2,
    LOCAL_SOURCE: 3,
    PATH_SOURCE: 4,
}


@dataclass(frozen=True)
class SkillSelection:
    """Generated selector and optional managed copy for one skill.

    Attributes:
        entry: Generated ``skills.config`` table.
        copy: Managed project copy required by the selection, if any.
    """

    entry: dict[str, Any]
    copy: SkillCopy | None = None


def select_skill(
    skill: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    enabled: bool,
    previous_copies: dict[str, SkillCopy],
) -> SkillSelection:
    """Resolve one configured reference to its generated representation.

    Args:
        skill: Skill reference from project configuration.
        cwd: Current project root.
        codex_home: Original Codex home directory.
        codexmgr_home: codexmgr-managed home directory.
        enabled: Desired enabled state.
        previous_copies: Previously managed copies rebound to this project.

    Returns:
        Portable selector and any required managed copy.

    Raises:
        CommandError: If a reference or generated name is ambiguous, an
            explicit path is missing, or selected metadata is invalid.
    """
    candidates = skill_reference_candidates(skill, cwd, codex_home, codexmgr_home)
    candidates = _deduplicate_sources(
        _without_managed_mirrors(candidates, previous_copies)
    )
    if not candidates:
        if is_named_skill(skill):
            return SkillSelection({"name": skill, "enabled": enabled})
        raise CommandError(f"Skill path not found: {skill}")
    if len(candidates) > 1:
        _raise_ambiguous_reference(skill, candidates)

    source = candidates[0]
    if source.source_type in {CODEXMGR_HOME_SOURCE, LOCAL_SOURCE}:
        declared_name = _validated_name_selector(
            source,
            cwd,
            codex_home,
            codexmgr_home,
            previous_copies,
        )
        entry = {"name": declared_name, "enabled": enabled}
        if source.source_type == CODEXMGR_HOME_SOURCE and enabled:
            copy = SkillCopy(
                source.name,
                source.skill_dir,
                project_skill_dir(cwd, source.name),
            )
            return SkillSelection(entry, copy)
        return SkillSelection(entry)
    return SkillSelection({"path": str(source.skill_file), "enabled": enabled})


def _validated_name_selector(
    selected: SkillSource,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    previous_copies: dict[str, SkillCopy],
) -> str:
    """Read and verify a name selector against every discoverable skill.

    Args:
        selected: Source selected by the configured reference.
        cwd: Current project root.
        codex_home: Original Codex home directory.
        codexmgr_home: codexmgr-managed home directory.
        previous_copies: Previously managed copies rebound to this project.

    Returns:
        Validated frontmatter name.

    Raises:
        CommandError: If metadata is invalid or the name is ambiguous.
    """
    declared_name = read_skill_name(selected.skill_file)
    available = all_named_skill_sources(cwd, codex_home, codexmgr_home)
    available = _deduplicate_sources(
        _without_managed_mirrors(available, previous_copies)
    )
    matches = [
        source
        for source in available
        if try_read_skill_name(source.skill_file) == declared_name
    ]
    if len(matches) > 1:
        _raise_ambiguous_declared_name(declared_name, matches)
    return declared_name


def _without_managed_mirrors(
    sources: list[SkillSource],
    previous_copies: dict[str, SkillCopy],
) -> list[SkillSource]:
    """Exclude project sources known to mirror a codexmgr-home source.

    Args:
        sources: Candidate or globally available sources.
        previous_copies: Previously managed copies rebound to this project.

    Returns:
        Sources without lock-recorded local mirrors when their source exists.
    """
    source_dirs = {
        source.skill_dir.resolve()
        for source in sources
        if source.source_type == CODEXMGR_HOME_SOURCE
    }
    managed_targets = {
        copy.target.resolve()
        for copy in previous_copies.values()
        if copy.source.resolve() in source_dirs
    }
    return [
        source
        for source in sources
        if not (
            source.source_type == LOCAL_SOURCE
            and source.skill_dir.resolve() in managed_targets
        )
    ]


def _deduplicate_sources(sources: list[SkillSource]) -> list[SkillSource]:
    """Collapse sources that resolve to the same physical skill directory.

    Args:
        sources: Sources that may overlap because stores share a root or link.

    Returns:
        One preferred source per physical skill directory.
    """
    unique: dict[Path, SkillSource] = {}
    for source in sources:
        key = source.skill_dir.resolve()
        current = unique.get(key)
        if current is None or _SOURCE_RANKS[source.source_type] > _SOURCE_RANKS[
            current.source_type
        ]:
            unique[key] = source
    return list(unique.values())


def _raise_ambiguous_reference(skill: str, sources: list[SkillSource]) -> None:
    """Raise a diagnostic for a bare reference with multiple sources.

    Args:
        skill: Ambiguous configured reference.
        sources: Sources matched by the reference.
    """
    details = _source_details(sources)
    raise CommandError(
        f"Ambiguous skill reference: {skill}\n"
        f"Found:\n{details}\n"
        "Configure an explicit path to select one."
    )


def _raise_ambiguous_declared_name(
    declared_name: str,
    sources: list[SkillSource],
) -> None:
    """Raise a diagnostic for a selector name declared by many skills.

    Args:
        declared_name: Ambiguous frontmatter name.
        sources: Sources declaring that name.
    """
    details = _source_details(sources)
    raise CommandError(
        f"Ambiguous declared skill name: {declared_name}\n"
        f"Found:\n{details}\n"
        "Configure an explicit path to select one."
    )


def _source_details(sources: list[SkillSource]) -> str:
    """Format skill sources for an ambiguity diagnostic.

    Args:
        sources: Sources to describe.

    Returns:
        Newline-delimited source labels and absolute skill-file paths.
    """
    return "\n".join(
        f"- {_SOURCE_LABELS[source.source_type]}: {source.skill_file}"
        for source in sources
    )
