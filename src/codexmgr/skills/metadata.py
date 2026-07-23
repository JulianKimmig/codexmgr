"""Read and validate metadata declared by Codex skill instruction files."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from yaml import YAMLError

from ..core.errors import CommandError


def read_skill_name(skill_file: Path) -> str:
    """Return the non-empty skill name declared in YAML frontmatter.

    Args:
        skill_file: Existing ``SKILL.md`` file to inspect.

    Returns:
        The trimmed frontmatter ``name`` value.

    Raises:
        CommandError: When frontmatter is missing, malformed, or has no valid
            ``name`` value.
    """
    metadata = _read_frontmatter(skill_file)
    name = metadata.get("name")
    if not isinstance(name, str) or not name.strip():
        raise _metadata_error(skill_file, "name must be a non-empty string")
    return name.strip()


def try_read_skill_name(skill_file: Path) -> str | None:
    """Return a declared skill name or ``None`` for unrelated invalid files.

    Args:
        skill_file: Existing ``SKILL.md`` file to inspect.

    Returns:
        The declared name when metadata is valid, otherwise ``None``.
    """
    try:
        return read_skill_name(skill_file)
    except CommandError:
        return None


def _read_frontmatter(skill_file: Path) -> Mapping[str, Any]:
    """Parse the YAML mapping at the beginning of one skill file.

    Args:
        skill_file: Existing ``SKILL.md`` file to inspect.

    Returns:
        Parsed YAML frontmatter mapping.

    Raises:
        CommandError: When the frontmatter boundaries or YAML are invalid.
    """
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise _metadata_error(skill_file, "missing YAML frontmatter")
    closing_index = _closing_boundary(lines)
    if closing_index is None:
        raise _metadata_error(skill_file, "missing YAML frontmatter closing boundary")
    try:
        parsed = yaml.safe_load("\n".join(lines[1:closing_index]))
    except YAMLError as exc:
        raise _metadata_error(skill_file, "invalid YAML frontmatter") from exc
    if not isinstance(parsed, Mapping):
        raise _metadata_error(skill_file, "YAML frontmatter must be a mapping")
    return parsed


def _closing_boundary(lines: list[str]) -> int | None:
    """Return the closing frontmatter-boundary index when present.

    Args:
        lines: Complete skill file split into lines.

    Returns:
        Closing boundary index, or ``None`` when it is missing.
    """
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return index
    return None


def _metadata_error(skill_file: Path, detail: str) -> CommandError:
    """Build one consistently formatted metadata error.

    Args:
        skill_file: Invalid skill instruction file.
        detail: Focused validation failure.

    Returns:
        Command error containing the resolved file location and detail.
    """
    return CommandError(f"Invalid skill metadata in {skill_file.resolve()}: {detail}")
