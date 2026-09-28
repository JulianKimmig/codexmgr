"""Resolve skill references across project and home skill stores."""

from dataclasses import dataclass
from pathlib import Path

from ..core.errors import CommandError
from ..core.paths import CODEXMGR_HOME_SOURCE
from .discovery import matching_paths, skill_paths

CODEX_HOME_SOURCE = "codex_home"
LOCAL_SOURCE = "local"
PATH_SOURCE = "path"


@dataclass(frozen=True)
class SkillSource:
    """Resolved skill source.

    Attributes:
        name: Skill name or configured reference.
        skill_file: Absolute path to the source SKILL.md file.
        source_type: Source store identifier.
    """

    name: str
    skill_file: Path
    source_type: str

    @property
    def skill_dir(self) -> Path:
        """Return the directory containing the skill file.

        Returns:
            Parent directory for the resolved SKILL.md file.
        """
        return self.skill_file.parent


def available_skill_names(cwd: Path, codex_home: Path, codexmgr_home: Path) -> list[str]:
    """List store-relative skill references available in configured stores.

    Args:
        cwd: Project directory whose local .agents skills should be inspected.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Sorted unique references, including group folders for nested skills.
    """
    codexmgr_names = set(_home_skill_names(codexmgr_home))
    codex_names = set(_home_skill_names(codex_home))
    _raise_duplicate_home_skill(codexmgr_names, codex_names, codexmgr_home, codex_home)
    return sorted(codexmgr_names | codex_names | set(_local_skill_names(cwd)))


def resolve_skill_reference(
    skill: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> SkillSource | None:
    """Resolve a skill name or path to a source.

    Args:
        skill: Skill name or path from project config.
        cwd: Project directory used for relative paths and local skills.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved skill source, or None when no SKILL.md exists.
    """
    source = _resolve_named_skill(skill, cwd, codex_home, codexmgr_home)
    if source is not None:
        return source
    if is_named_skill(skill):
        return None
    return _resolve_path_skill(skill, cwd)


def resolve_skill_file(
    skill: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> Path | None:
    """Resolve a skill reference to a SKILL.md path.

    Args:
        skill: Skill name or path from project config.
        cwd: Project directory used for relative paths and local skills.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved SKILL.md path, or None when the skill is missing.
    """
    source = resolve_skill_reference(skill, cwd, codex_home, codexmgr_home)
    return None if source is None else source.skill_file


def is_named_skill(skill: str) -> bool:
    """Return whether a skill reference is a bare name.

    Args:
        skill: Skill reference from project configuration or CLI input.

    Returns:
        True when the reference should be resolved by name.
    """
    raw = skill.strip()
    return "/" not in raw and "\\" not in raw and raw != "SKILL.md"


def project_skill_dir(cwd: Path, name: str) -> Path:
    """Return the project-local skill directory for a named skill.

    Args:
        cwd: Project directory.
        name: Bare skill name.

    Returns:
        Path to .agents/skills/<name>.
    """
    return cwd / ".agents" / "skills" / name


def _resolve_named_skill(
    name: str,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> SkillSource | None:
    """Resolve a bare or group-qualified reference for read-only callers.

    Args:
        name: Bare skill name or store-relative reference.
        cwd: Project directory used for local skills.
        codex_home: Codex home directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved skill source, or None.
    """
    manager = matching_paths(codexmgr_home / "skills", name)
    codex = matching_paths(codex_home / "skills", name)
    if manager and codex and not _same_path(codexmgr_home, codex_home):
        raise CommandError(f"Skill exists in both CODEXMGR_HOME and CODEX_HOME: {name}")
    stores = [
        (codexmgr_home / "skills", manager, CODEXMGR_HOME_SOURCE),
        (codex_home / "skills", codex, CODEX_HOME_SOURCE),
        (
            cwd / ".agents" / "skills",
            matching_paths(cwd / ".agents" / "skills", name),
            LOCAL_SOURCE,
        ),
    ]
    for root, references, kind in stores:
        if len(references) > 1:
            raise CommandError(f"Ambiguous skill reference: {name}: {', '.join(references)}")
        if references:
            reference = references[0]
            return SkillSource(reference, (root / reference / "SKILL.md").resolve(), kind)
    return None


def _resolve_path_skill(skill: str, cwd: Path) -> SkillSource | None:
    """Resolve a path-like skill reference.

    Args:
        skill: Path-like skill reference.
        cwd: Project directory used for relative paths.

    Returns:
        Resolved path source, or None.
    """
    path = Path(skill).expanduser()
    if not path.is_absolute():
        path = cwd / path
    skill_file = path if path.name == "SKILL.md" else path / "SKILL.md"
    if not skill_file.is_file():
        return None
    return SkillSource(skill, skill_file.resolve(), PATH_SOURCE)


def _home_skill_names(home: Path) -> list[str]:
    """List named skills in one home directory.

    Args:
        home: Home directory to inspect.

    Returns:
        Sorted skill names with a SKILL.md file.
    """
    return skill_paths(home / "skills")


def _local_skill_names(cwd: Path) -> list[str]:
    """List project-local skill names.

    Args:
        cwd: Project directory to inspect.

    Returns:
        Sorted local skill names with a SKILL.md file.
    """
    return skill_paths(cwd / ".agents" / "skills")


def _raise_duplicate_home_skill(
    codexmgr_names: set[str],
    codex_names: set[str],
    codexmgr_home: Path,
    codex_home: Path,
) -> None:
    """Raise for duplicate skill names across distinct home stores.

    Args:
        codexmgr_names: Skills from CODEXMGR_HOME.
        codex_names: Skills from CODEX_HOME.
        codexmgr_home: codexmgr home directory.
        codex_home: Codex home directory.
    """
    if _same_path(codexmgr_home, codex_home):
        return
    duplicates = sorted(codexmgr_names & codex_names)
    if duplicates:
        raise CommandError(
            f"Skill exists in both CODEXMGR_HOME and CODEX_HOME: {duplicates[0]}"
        )


def _same_path(left: Path, right: Path) -> bool:
    """Return whether two paths resolve to the same location.

    Args:
        left: First path.
        right: Second path.

    Returns:
        True when the paths resolve to the same filesystem location.
    """
    return left.resolve() == right.resolve()
