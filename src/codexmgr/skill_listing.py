"""Read-only listing helpers for Codex skills."""

from dataclasses import dataclass
from pathlib import Path

from .paths import config_path
from .skills import _resolve_skill_file, _skill_lists
from .toml_io import load_optional_toml_file


@dataclass(frozen=True)
class SkillListItem:
    """Display state for one known skill name or reference.

    Attributes:
        name: Skill name or configured reference.
        state: One of ``available``, ``enabled``, or ``disabled``.
        missing: Whether a configured skill reference does not resolve.
    """

    name: str
    state: str
    missing: bool = False


def skill_list_lines(cwd: Path, codex_home: Path) -> list[str]:
    """Build display lines for available and configured skills.

    Args:
        cwd: Project directory whose configured skills should be read.
        codex_home: Global Codex home containing named skills.

    Returns:
        Sorted skill list lines suitable for CLI output.
    """
    return [_format_item(item) for item in list_skill_items(cwd, codex_home)]


def list_skill_items(cwd: Path, codex_home: Path) -> list[SkillListItem]:
    """List available and configured skills with project state.

    Args:
        cwd: Project directory whose configured skills should be read.
        codex_home: Global Codex home containing named skills.

    Returns:
        Skill items sorted by displayed name.
    """
    enabled, disabled = configured_skill_lists(cwd)
    available = set(_available_skill_names(codex_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [_skill_item(name, enabled, disabled, available, cwd, codex_home) for name in names]


def configured_skill_lists(cwd: Path) -> tuple[list[str], list[str]]:
    """Read configured enabled and disabled skill references.

    Args:
        cwd: Project directory whose codexmgr.toml should be read when present.

    Returns:
        Enabled and disabled skill reference lists.
    """
    return _skill_lists(load_optional_toml_file(config_path(cwd)))


def missing_enabled_skills(cwd: Path, codex_home: Path) -> list[str]:
    """Return enabled skill references that do not resolve to SKILL.md.

    Args:
        cwd: Project directory whose configured skills should be read.
        codex_home: Global Codex home containing named skills.

    Returns:
        Enabled skill references that are currently missing.
    """
    enabled, _ = configured_skill_lists(cwd)
    return [skill for skill in enabled if _resolve_skill_file(skill, cwd, codex_home) is None]


def _available_skill_names(codex_home: Path) -> list[str]:
    """List named skills available under CODEX_HOME.

    Args:
        codex_home: Global Codex home containing named skills.

    Returns:
        Sorted skill directory names containing a SKILL.md file.
    """
    skills_dir = codex_home / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in skills_dir.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def _skill_item(
    name: str,
    enabled: list[str],
    disabled: list[str],
    available: set[str],
    cwd: Path,
    codex_home: Path,
) -> SkillListItem:
    """Build one skill list item.

    Args:
        name: Skill name or configured reference.
        enabled: Enabled skill references.
        disabled: Disabled skill references.
        available: Available named skills.
        cwd: Project directory used to resolve configured path skills.
        codex_home: Global Codex home containing named skills.

    Returns:
        Display item for the skill.
    """
    if name in enabled:
        return SkillListItem(name, "enabled", _is_missing(name, cwd, codex_home))
    if name in disabled:
        return SkillListItem(name, "disabled", _is_missing(name, cwd, codex_home))
    return SkillListItem(name, "available", name not in available)


def _is_missing(name: str, cwd: Path, codex_home: Path) -> bool:
    """Return whether a configured skill reference is missing.

    Args:
        name: Configured skill reference.
        cwd: Project directory used to resolve path skills.
        codex_home: Global Codex home containing named skills.

    Returns:
        True when no SKILL.md file resolves for the reference.
    """
    return _resolve_skill_file(name, cwd, codex_home) is None


def _format_item(item: SkillListItem) -> str:
    """Format one skill list item.

    Args:
        item: Skill list item to format.

    Returns:
        Human-readable CLI line.
    """
    suffix = " (missing)" if item.missing else ""
    return f"{item.state} {item.name}{suffix}"
