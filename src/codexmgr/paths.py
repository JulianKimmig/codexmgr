"""Filesystem path helpers for codexmgr project and home directories."""

import os
from pathlib import Path

from .errors import CommandError


def global_codex_dir() -> Path:
    """Return the Codex home directory.

    Returns:
        CODEX_HOME when set, otherwise ~/.codex.
    """
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def global_codexmgr_dir() -> Path:
    """Return the codexmgr home directory.

    Returns:
        CODEXMGR_HOME when set, otherwise ~/.codexmgr.
    """
    return Path(os.environ.get("CODEXMGR_HOME", Path.home() / ".codexmgr"))


def global_codex_config_path(codex_home: Path) -> Path:
    """Return the user-level Codex config path.

    Args:
        codex_home: Codex home directory.

    Returns:
        Path to CODEX_HOME/config.toml.
    """
    return codex_home / "config.toml"


def project_codex_dir(cwd: Path) -> Path:
    """Return the project-local .codex directory path.

    Args:
        cwd: Project directory.

    Returns:
        The project .codex directory path.
    """
    return cwd / ".codex"


def config_path(cwd: Path) -> Path:
    """Return the project codexmgr.toml path.

    Args:
        cwd: Project directory.

    Returns:
        Path to .codex/codexmgr.toml.
    """
    return project_codex_dir(cwd) / "codexmgr.toml"


def lock_path(cwd: Path) -> Path:
    """Return the project codexmgr lockfile path.

    Args:
        cwd: Project directory.

    Returns:
        Path to .codex/codexmgr.lock.
    """
    return project_codex_dir(cwd) / "codexmgr.lock"


def codex_config_path(cwd: Path) -> Path:
    """Return the generated project Codex config path.

    Args:
        cwd: Project directory.

    Returns:
        Path to .codex/config.toml.
    """
    return project_codex_dir(cwd) / "config.toml"


def agents_md_path(cwd: Path) -> Path:
    """Return the project AGENTS.md path.

    Args:
        cwd: Project directory.

    Returns:
        Path to AGENTS.md in the project root.
    """
    return cwd / "AGENTS.md"


def resolve_template(reference: str, cwd: Path, codexmgr_home: Path) -> tuple[str, Path]:
    """Resolve an AGENTS.md template reference to a source id and file path.

    Args:
        reference: Named template reference or path-like TOML file reference.
        cwd: Project directory used for relative path references.
        codexmgr_home: codexmgr home used for named template references.

    Returns:
        The source identifier and resolved template path.
    """
    if _is_named_template(reference):
        source_id = reference
        path = codexmgr_home / "agentsmd" / f"{reference}.toml"
    else:
        path = _expand_path(reference, cwd)
        source_id = path.stem

    if not path.is_file():
        raise CommandError(f"Template not found: {path}")

    return source_id, path


def _is_named_template(reference: str) -> bool:
    """Return whether a template reference should resolve by name.

    Args:
        reference: Template reference from project configuration or CLI input.

    Returns:
        True when the reference is a bare template name.
    """
    raw = reference.strip()
    return "/" not in raw and "\\" not in raw and not raw.endswith(".toml")


def _expand_path(reference: str, cwd: Path) -> Path:
    """Expand a path-like template reference.

    Args:
        reference: Path-like template reference.
        cwd: Project directory used for relative references.

    Returns:
        Absolute or project-relative template path.
    """
    path = Path(reference).expanduser()
    if path.is_absolute():
        return path
    return cwd / path
