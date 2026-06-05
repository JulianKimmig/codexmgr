"""Manage skill enable and disable lists in project configuration."""

from pathlib import Path
from typing import Any

from .errors import CommandError
from .paths import codex_config_path, config_path, project_codex_dir
from .toml_io import load_optional_toml_file, write_toml_file


def enable_skill(skill: str, cwd: Path) -> str:
    """Add a skill to [skills].enabled and remove it from disabled.

    Args:
        skill: Skill name or path to record in the project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.

    Returns:
        The skill value that was enabled.
    """
    return _set_skill_state(skill, cwd, enabled=True)


def disable_skill(skill: str, cwd: Path) -> str:
    """Add a skill to [skills].disabled and remove it from enabled.

    Args:
        skill: Skill name or path to record in the project configuration.
        cwd: Project directory whose .codex/codexmgr.toml should be updated.

    Returns:
        The skill value that was disabled.
    """
    return _set_skill_state(skill, cwd, enabled=False)


def build_codex_skill_config(
    entries: list[dict[str, Any]],
    cwd: Path,
) -> dict[str, Any] | None:
    """Build .codex/config.toml content for configured skill states.

    Args:
        entries: Resolved skills.config entries to write.
        cwd: Project directory whose .codex/config.toml should be updated.

    Returns:
        A parsed .codex/config.toml document with updated skills.config entries,
        or None when no skills are configured.
    """
    if not entries:
        return None

    codex_config = load_optional_toml_file(codex_config_path(cwd))
    skills = codex_config.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise CommandError(".codex/config.toml [skills] must be a table")
    skills["config"] = entries
    return codex_config


def resolve_codex_skill_entries(
    project_config: dict[str, Any],
    cwd: Path,
    codex_home: Path,
) -> list[dict[str, Any]]:
    """Resolve configured project skills into Codex skill config entries.

    Args:
        project_config: Parsed .codex/codexmgr.toml content.
        cwd: Project directory used to resolve relative skill paths.
        codex_home: Global Codex home used to resolve named skills.

    Returns:
        A list of dictionaries suitable for [[skills.config]] entries.
    """
    enabled_skills, disabled_skills = _skill_lists(project_config)
    return [
        *_skill_config_entries(enabled_skills, cwd, codex_home, enabled=True),
        *_skill_config_entries(disabled_skills, cwd, codex_home, enabled=False),
    ]


def _set_skill_state(skill: str, cwd: Path, *, enabled: bool) -> str:
    _require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    enabled_skills, disabled_skills = _skill_lists(config)

    if enabled:
        enabled_skills = _append_once(enabled_skills, skill)
        disabled_skills = _without(disabled_skills, skill)
    else:
        disabled_skills = _append_once(disabled_skills, skill)
        enabled_skills = _without(enabled_skills, skill)

    _set_skill_lists(config, enabled_skills, disabled_skills)
    write_toml_file(config_path(cwd), config)
    return skill


def _require_codex_dir(cwd: Path) -> Path:
    codex_dir = project_codex_dir(cwd)
    if not codex_dir.is_dir():
        raise CommandError(f"Project .codex directory not found: {codex_dir}")
    return codex_dir


def _skill_lists(config: dict[str, Any]) -> tuple[list[str], list[str]]:
    skills = config.get("skills", {})
    if not isinstance(skills, dict):
        raise CommandError("codexmgr.toml [skills] must be a table")
    return _string_list(skills, "enabled"), _string_list(skills, "disabled")


def _string_list(table: dict[str, Any], key: str) -> list[str]:
    values = table.get(key, [])
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise CommandError(f"codexmgr.toml skills.{key} must be a list of strings")
    return list(values)


def _set_skill_lists(config: dict[str, Any], enabled: list[str], disabled: list[str]) -> None:
    skills = config.setdefault("skills", {})
    if not isinstance(skills, dict):
        raise CommandError("codexmgr.toml [skills] must be a table")
    skills["enabled"] = enabled
    skills["disabled"] = disabled


def _append_once(values: list[str], value: str) -> list[str]:
    if value in values:
        return values
    return [*values, value]


def _without(values: list[str], value: str) -> list[str]:
    return [item for item in values if item != value]


def _skill_config_entries(
    skills: list[str],
    cwd: Path,
    codex_home: Path,
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    return [
        _skill_config_entry(skill, cwd, codex_home, enabled=enabled)
        for skill in skills
    ]


def _skill_config_entry(
    skill: str,
    cwd: Path,
    codex_home: Path,
    *,
    enabled: bool,
) -> dict[str, Any]:
    skill_file = _resolve_skill_file(skill, cwd, codex_home)
    if skill_file is None:
        return {"name": skill, "enabled": enabled}
    return {"path": str(skill_file), "enabled": enabled}


def _resolve_skill_file(skill: str, cwd: Path, codex_home: Path) -> Path | None:
    if _is_named_skill(skill):
        skill_file = codex_home / "skills" / skill / "SKILL.md"
    else:
        path = Path(skill).expanduser()
        if not path.is_absolute():
            path = cwd / path
        skill_file = path if path.name == "SKILL.md" else path / "SKILL.md"

    if not skill_file.is_file():
        return None
    return skill_file.resolve()


def _is_named_skill(skill: str) -> bool:
    raw = skill.strip()
    return "/" not in raw and "\\" not in raw and raw != "SKILL.md"
