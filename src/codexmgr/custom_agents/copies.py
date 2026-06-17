"""Manage project-local copies of codexmgr-home custom agents."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value


@dataclass(frozen=True)
class AgentCopy:
    """A managed custom-agent file copy.

    Attributes:
        name: Bare custom-agent name.
        source: Source TOML file under CODEXMGR_HOME.
        target: Project-local .codex custom-agent file.
    """

    name: str
    source: Path
    target: Path


@dataclass(frozen=True)
class AgentCopyFile:
    """Expected file content for a managed custom-agent copy.

    Attributes:
        path: Project-local copied file path.
        content: Expected byte content from the source file.
    """

    path: Path
    content: bytes


def validate_agent_copy_targets(
    copies: list[AgentCopy],
    previous_lock: Mapping[str, Any],
) -> None:
    """Reject first-time copies over unmanaged target files.

    Args:
        copies: Current managed agent copies to create or refresh.
        previous_lock: Previous codexmgr lock data.
    """
    previous = previous_agent_copies(previous_lock)
    for copy in copies:
        if copy.name not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged agent copy: {copy.target}")


def previous_agent_copies(previous_lock: Mapping[str, Any]) -> dict[str, AgentCopy]:
    """Read managed custom-agent copy metadata from previous lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.

    Returns:
        Previous managed copies keyed by custom-agent name.
    """
    raw_copies = plain_toml_value(previous_lock.get("agents", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock agents.copies must be a list")
    copies: dict[str, AgentCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy)
        copies[copy.name] = copy
    return copies


def obsolete_agent_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[AgentCopy],
) -> list[Path]:
    """Return previous managed custom-agent targets absent from current state.

    Args:
        previous_lock: Previous codexmgr lock data.
        current_copies: Current managed custom-agent copies.

    Returns:
        Sorted target files to remove.
    """
    current_names = {copy.name for copy in current_copies}
    return sorted(
        copy.target
        for name, copy in previous_agent_copies(previous_lock).items()
        if name not in current_names
    )


def agent_copy_lock_entries(copies: list[AgentCopy]) -> list[dict[str, str]]:
    """Build lockfile entries for managed custom-agent copies.

    Args:
        copies: Current managed custom-agent copies.

    Returns:
        Lockfile table entries.
    """
    return [
        {
            "name": copy.name,
            "source": str(copy.source.resolve()),
            "target": str(copy.target.resolve()),
        }
        for copy in copies
    ]


def expected_agent_copy_files(copies: list[AgentCopy]) -> list[AgentCopyFile]:
    """Build expected file contents for managed custom-agent copies.

    Args:
        copies: Current managed custom-agent copies.

    Returns:
        Expected copied files in stable order.
    """
    return [AgentCopyFile(copy.target, copy.source.read_bytes()) for copy in copies]


def apply_agent_copy(copy: AgentCopy) -> None:
    """Copy one managed custom-agent TOML file into the project.

    Args:
        copy: Managed custom-agent copy to refresh.
    """
    copy.target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(copy.source, copy.target)


def remove_agent_copy_target(target: Path) -> None:
    """Remove a previously managed custom-agent target.

    Args:
        target: Project-local copied custom-agent path to remove.
    """
    if target.exists():
        target.unlink()


def _copy_from_lock_entry(raw_copy: Any) -> AgentCopy:
    """Parse one custom-agent copy lock entry.

    Args:
        raw_copy: Plain lock entry value.

    Returns:
        Parsed managed custom-agent copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock agents.copies entries must be tables")
    name = raw_copy.get("name")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if not isinstance(name, str) or not isinstance(source, str) or not isinstance(target, str):
        raise CommandError("codexmgr.lock agents.copies entries must include name, source, and target")
    return AgentCopy(name, Path(source), Path(target))
