"""Launch-mode parsing and project-local Codex environment preparation."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class CodexLaunchRequest:
    """A parsed request to launch Codex in managed or simple mode.

    Attributes:
        simple: Whether to bypass all codexmgr project preparation.
        codex_args: Arguments to proxy to the external Codex executable.
    """

    simple: bool
    codex_args: list[str]


def parse_codex_launch_request(codex_args: list[str]) -> CodexLaunchRequest:
    """Parse the optional leading codexmgr ``--simple`` launch flag.

    Args:
        codex_args: Raw arguments following ``codexmgr codex``.

    Returns:
        The selected launch mode and external Codex arguments.
    """
    if codex_args[:1] == ["--simple"]:
        return CodexLaunchRequest(simple=True, codex_args=codex_args[1:])
    return CodexLaunchRequest(simple=False, codex_args=list(codex_args))


def build_project_codex_environment(
    cwd: Path,
    stderr: TextIO,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the child environment for a project-local Codex launch.

    Args:
        cwd: Project directory whose local Codex home may be selected.
        stderr: Stream that receives a missing-auth warning.
        environ: Source process environment, or ``os.environ`` when omitted.

    Returns:
        A copied child environment. ``CODEX_HOME`` points to ``.codex`` when
        that directory contains ``config.toml``.
    """
    environment = dict(os.environ if environ is None else environ)
    project_codex_dir = cwd / ".codex"
    if not (project_codex_dir / "config.toml").is_file():
        return environment

    project_codex_dir.mkdir(parents=True, exist_ok=True)
    environment["CODEX_HOME"] = str(project_codex_dir)
    global_auth = _global_auth_path(environment)
    if global_auth.is_file():
        _replace_auth_link(project_codex_dir / "auth.json", global_auth)
    else:
        stderr.write(
            "codexmgr codex: warning: no global auth found at "
            f"{global_auth}; you may need to auth once.\n"
        )
    return environment


def _global_auth_path(environment: Mapping[str, str]) -> Path:
    """Resolve the read-only global authentication source.

    Args:
        environment: Launch environment containing HOME and optional override.

    Returns:
        ``CODEX_GLOBAL_AUTH`` when non-empty, otherwise HOME's Codex auth path.
    """
    configured_auth = environment.get("CODEX_GLOBAL_AUTH")
    if configured_auth:
        return Path(configured_auth)
    return Path(environment["HOME"]) / ".codex" / "auth.json"


def _replace_auth_link(auth_link: Path, global_auth: Path) -> None:
    """Replace the project auth entry with a link to global authentication.

    Args:
        auth_link: Project-local ``.codex/auth.json`` link path.
        global_auth: Existing global authentication source file.

    Returns:
        None. Any existing file or symbolic link at ``auth_link`` is replaced.
    """
    if auth_link.exists() or auth_link.is_symlink():
        auth_link.unlink()
    auth_link.symlink_to(global_auth)
