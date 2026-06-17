"""Resolve reusable Codex custom-agent sources from CODEXMGR_HOME."""

from dataclasses import dataclass
from pathlib import Path

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file


@dataclass(frozen=True)
class AgentSource:
    """Resolved custom-agent source.

    Attributes:
        name: Bare custom-agent name.
        source_file: Source TOML file under CODEXMGR_HOME.
    """

    name: str
    source_file: Path


def available_agent_names(codexmgr_home: Path) -> list[str]:
    """List custom-agent names available under CODEXMGR_HOME.

    Args:
        codexmgr_home: codexmgr home directory.

    Returns:
        Sorted custom-agent names with a TOML source file.
    """
    root = agent_sources_dir(codexmgr_home)
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.iterdir() if _is_agent_file(path))


def resolve_agent_source(name: str, codexmgr_home: Path) -> AgentSource | None:
    """Resolve one custom-agent source by bare name.

    Args:
        name: Custom-agent name from project configuration.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved source, or None when the source file is absent.
    """
    if not is_bare_agent_name(name):
        return None
    path = agent_source_file(codexmgr_home, name)
    if not path.is_file():
        return None
    return AgentSource(name, path.resolve())


def require_agent_source(name: str, codexmgr_home: Path) -> AgentSource:
    """Resolve one custom-agent source or raise a user-facing error.

    Args:
        name: Custom-agent name from the CLI.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved custom-agent source.
    """
    if not is_bare_agent_name(name):
        raise CommandError(f"Agent name must be a bare name: {name}")
    source = resolve_agent_source(name, codexmgr_home)
    if source is None:
        raise CommandError(f"Agent not found: {agent_source_file(codexmgr_home, name)}")
    load_toml_file(source.source_file)
    return source


def agent_source_file(codexmgr_home: Path, name: str) -> Path:
    """Return the expected source file path for a named custom agent.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare custom-agent name.

    Returns:
        Path to CODEXMGR_HOME/agents/<name>.toml.
    """
    return agent_sources_dir(codexmgr_home) / f"{name}.toml"


def agent_sources_dir(codexmgr_home: Path) -> Path:
    """Return the codexmgr-home custom-agent source directory.

    Args:
        codexmgr_home: codexmgr home directory.

    Returns:
        Path to CODEXMGR_HOME/agents.
    """
    return codexmgr_home / "agents"


def project_agent_path(cwd: Path, name: str) -> Path:
    """Return the project-local custom-agent target path.

    Args:
        cwd: Project directory.
        name: Bare custom-agent name.

    Returns:
        Path to .codex/agents/<name>.toml.
    """
    return cwd / ".codex" / "agents" / f"{name}.toml"


def is_bare_agent_name(name: str) -> bool:
    """Return whether a custom-agent reference is a bare name.

    Args:
        name: Custom-agent reference from project configuration or CLI input.

    Returns:
        True when the reference has no path separators or TOML suffix.
    """
    raw = name.strip()
    return bool(raw) and "/" not in raw and "\\" not in raw and not raw.endswith(".toml")


def _is_agent_file(path: Path) -> bool:
    """Return whether a path is a top-level custom-agent TOML file.

    Args:
        path: Candidate source path.

    Returns:
        True when the path is a file with a .toml suffix.
    """
    return path.is_file() and path.suffix == ".toml"
