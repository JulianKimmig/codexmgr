"""Resolve reusable Codex hook bundles from CODEXMGR_HOME."""

from dataclasses import dataclass
from pathlib import Path

from ..core.errors import CommandError


@dataclass(frozen=True)
class HookSource:
    """Resolved hook bundle source.

    Attributes:
        name: Bare hook bundle name.
        hook_dir: Source directory under CODEXMGR_HOME.
        config_file: Source hooks.json path.
    """

    name: str
    hook_dir: Path
    config_file: Path


def available_hook_names(codexmgr_home: Path) -> list[str]:
    """List named hook bundles available under CODEXMGR_HOME.

    Args:
        codexmgr_home: codexmgr home directory.

    Returns:
        Sorted hook bundle names with a hooks.json file.
    """
    hooks_dir = codexmgr_home / "hooks"
    if not hooks_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in hooks_dir.iterdir()
        if path.is_dir() and (path / "hooks.json").is_file()
    )


def resolve_hook_source(name: str, codexmgr_home: Path) -> HookSource | None:
    """Resolve one bare hook bundle name.

    Args:
        name: Hook bundle name from project configuration.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved hook source, or None when no hooks.json exists.
    """
    if not is_bare_hook_name(name):
        return None
    config_file = hook_bundle_file(codexmgr_home, name)
    if not config_file.is_file():
        return None
    return HookSource(name, config_file.parent.resolve(), config_file.resolve())


def require_hook_source(name: str, codexmgr_home: Path) -> HookSource:
    """Resolve one hook bundle or raise a user-facing error.

    Args:
        name: Hook bundle name from the CLI.
        codexmgr_home: codexmgr home directory.

    Returns:
        Resolved hook source.
    """
    if not is_bare_hook_name(name):
        raise CommandError(f"Hook name must be a bare name: {name}")
    source = resolve_hook_source(name, codexmgr_home)
    if source is None:
        raise CommandError(f"Hook bundle not found: {hook_bundle_file(codexmgr_home, name)}")
    return source


def hook_bundle_file(codexmgr_home: Path, name: str) -> Path:
    """Return the expected hooks.json path for a named hook bundle.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare hook bundle name.

    Returns:
        Path to CODEXMGR_HOME/hooks/<name>/hooks.json.
    """
    return codexmgr_home / "hooks" / name / "hooks.json"


def project_hooks_json_path(cwd: Path) -> Path:
    """Return the project-local hooks.json path.

    Args:
        cwd: Project directory.

    Returns:
        Path to .codex/hooks.json.
    """
    return cwd / ".codex" / "hooks.json"


def project_hook_dir(cwd: Path, name: str) -> Path:
    """Return the project-local managed hook bundle directory.

    Args:
        cwd: Project directory.
        name: Bare hook bundle name.

    Returns:
        Path to .codex/hooks/<name>.
    """
    return cwd / ".codex" / "hooks" / name


def is_bare_hook_name(name: str) -> bool:
    """Return whether a hook reference is a bare bundle name.

    Args:
        name: Hook reference from project configuration or CLI input.

    Returns:
        True when the reference has no path separators and is not empty.
    """
    raw = name.strip()
    return bool(raw) and "/" not in raw and "\\" not in raw
