"""Manage project-local copies of codexmgr-home custom agents."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.paths import CODEXMGR_HOME_SOURCE
from ..core.toml_io import plain_toml_value
from .sources import agent_source_file, is_bare_agent_name, project_agent_path


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
        source: Canonical custom-agent TOML file.
        path: Project-local copied file path.
        content: Expected byte content from the source file.
        resource_kind: Resource family used for conflict validation.
    """

    source: Path
    path: Path
    content: bytes
    resource_kind: str = "custom-agent"


def validate_agent_copy_targets(
    copies: list[AgentCopy],
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Reject first-time copies over unmanaged target files.

    Args:
        copies: Current managed agent copies to create or refresh.
        previous_lock: Previous codexmgr lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.
    """
    previous = previous_agent_copies(previous_lock, cwd, codexmgr_home)
    for copy in copies:
        if copy.name not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged agent copy: {copy.target}")


def previous_agent_copies(
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> dict[str, AgentCopy]:
    """Read managed custom-agent copy metadata from previous lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.

    Returns:
        Previous managed copies keyed by custom-agent name.
    """
    raw_copies = plain_toml_value(previous_lock.get("agents", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock agents.copies must be a list")
    copies: dict[str, AgentCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy, cwd, codexmgr_home)
        copies[copy.name] = copy
    return copies


def obsolete_agent_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[AgentCopy],
    cwd: Path,
    codexmgr_home: Path,
) -> list[Path]:
    """Return previous managed custom-agent targets absent from current state.

    Args:
        previous_lock: Previous codexmgr lock data.
        current_copies: Current managed custom-agent copies.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.

    Returns:
        Sorted target files to remove.
    """
    current_names = {copy.name for copy in current_copies}
    return sorted(
        copy.target
        for name, copy in previous_agent_copies(
            previous_lock,
            cwd,
            codexmgr_home,
        ).items()
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
            "source": CODEXMGR_HOME_SOURCE,
            "target": f".codex/agents/{copy.name}.toml",
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
    return [
        AgentCopyFile(copy.source, copy.target, copy.source.read_bytes())
        for copy in copies
    ]


def apply_agent_copy(copy: AgentCopy, skip_targets: set[Path] | None = None) -> None:
    """Copy one managed custom-agent TOML file into the project.

    Args:
        copy: Managed custom-agent copy to refresh.
        skip_targets: Exact target files to preserve for this apply.
    """
    if skip_targets is not None and copy.target.absolute() in skip_targets:
        return
    copy.target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(copy.source, copy.target)


def remove_agent_copy_target(target: Path) -> None:
    """Remove a previously managed custom-agent target.

    Args:
        target: Project-local copied custom-agent path to remove.
    """
    if target.exists():
        target.unlink()


def _copy_from_lock_entry(
    raw_copy: Any,
    cwd: Path,
    codexmgr_home: Path,
) -> AgentCopy:
    """Parse one custom-agent copy lock entry.

    Args:
        raw_copy: Plain lock entry value.
        cwd: Current project root used to rebind the target.
        codexmgr_home: Current manager home used to rebind the source.

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
    if name in {".", ".."} or not is_bare_agent_name(name):
        raise CommandError(
            "codexmgr.lock agents.copies entries must use a safe agent name"
        )
    return AgentCopy(
        name,
        agent_source_file(codexmgr_home, name),
        project_agent_path(cwd, name),
    )
