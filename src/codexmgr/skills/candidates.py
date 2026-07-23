"""Discover every source that may satisfy a configured skill reference."""

from pathlib import Path

from .sources import (
    CODEX_HOME_SOURCE,
    CODEXMGR_HOME_SOURCE,
    LOCAL_SOURCE,
    PATH_SOURCE,
    SkillSource,
    is_named_skill,
    project_skill_dir,
)


def skill_reference_candidates(
    skill: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[SkillSource]:
    """Return every existing source matching one configured reference.

    Args:
        skill: Bare skill name or explicit path reference.
        cwd: Project directory used for local and relative-path skills.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Matching sources in stable store-priority order.
    """
    if is_named_skill(skill):
        return _named_skill_candidates(skill, cwd, codex_home, codexmgr_home)
    source = _resolve_path_skill(skill, cwd)
    return [] if source is None else [source]


def all_named_skill_sources(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[SkillSource]:
    """Return all folder-addressable skill sources from configured stores.

    Args:
        cwd: Project directory whose local skills should be included.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Sources ordered by store and folder name.
    """
    stores = [
        (CODEXMGR_HOME_SOURCE, codexmgr_home / "skills"),
        (CODEX_HOME_SOURCE, codex_home / "skills"),
        (LOCAL_SOURCE, cwd / ".agents" / "skills"),
    ]
    sources: list[SkillSource] = []
    for source_type, root in stores:
        for name in _skill_names(root):
            skill_file = root / name / "SKILL.md"
            sources.append(SkillSource(name, skill_file.resolve(), source_type))
    return sources


def _named_skill_candidates(
    name: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[SkillSource]:
    """Return every store source whose folder matches a bare name.

    Args:
        name: Bare skill folder name.
        cwd: Project directory used for local skills.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Existing sources in codexmgr-home, Codex-home, then project order.
    """
    candidates = [
        SkillSource(
            name,
            (codexmgr_home / "skills" / name / "SKILL.md").resolve(),
            CODEXMGR_HOME_SOURCE,
        ),
        SkillSource(
            name,
            (codex_home / "skills" / name / "SKILL.md").resolve(),
            CODEX_HOME_SOURCE,
        ),
        SkillSource(
            name,
            (project_skill_dir(cwd, name) / "SKILL.md").resolve(),
            LOCAL_SOURCE,
        ),
    ]
    return [candidate for candidate in candidates if candidate.skill_file.is_file()]


def _resolve_path_skill(skill: str, cwd: Path) -> SkillSource | None:
    """Resolve a path-like reference without applying named-store priority.

    Args:
        skill: Path-like skill reference.
        cwd: Project directory used for relative paths.

    Returns:
        Resolved explicit source, or None when it does not exist.
    """
    path = Path(skill).expanduser()
    if not path.is_absolute():
        path = cwd / path
    skill_file = path if path.name == "SKILL.md" else path / "SKILL.md"
    if not skill_file.is_file():
        return None
    return SkillSource(skill, skill_file.resolve(), PATH_SOURCE)


def _skill_names(skills_dir: Path) -> list[str]:
    """Return sorted child-folder names containing a skill file.

    Args:
        skills_dir: Store directory containing named skill folders.

    Returns:
        Sorted folder names with an immediate ``SKILL.md`` child.
    """
    if not skills_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in skills_dir.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )
