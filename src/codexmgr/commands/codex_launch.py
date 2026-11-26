"""Launch-mode parsing and project-local Codex environment preparation."""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TextIO

from ..core.paths import project_codex_dir, project_codex_runtime_dir


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
    *,
    stdin: TextIO | None = None,
) -> dict[str, str]:
    """Build the child environment for a project-local Codex launch.

    Args:
        cwd: Project directory whose local Codex home may be selected.
        stderr: Stream that receives authentication warnings.
        environ: Source process environment, or ``os.environ`` when omitted.
        stdin: Optional terminal input for acknowledging the Windows auth warning.

    Returns:
        A copied child environment. ``CODEX_HOME`` points to
        ``.codex/.runtime`` when the project ``.codex`` directory contains
        ``config.toml``.
    """
    environment = dict(os.environ if environ is None else environ)
    config_dir = project_codex_dir(cwd)
    if not (config_dir / "config.toml").is_file():
        return environment

    runtime_dir = project_codex_runtime_dir(cwd)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    environment["CODEX_HOME"] = str(runtime_dir)
    global_auth = _global_auth_path(environment)
    if global_auth.is_file():
        auth_link = runtime_dir / "auth.json"
        try:
            _replace_auth_link(auth_link, global_auth)
        except OSError as exc:
            if getattr(exc, "winerror", None) != 1314:  # ERROR_PRIVILEGE_NOT_HELD
                raise
            if not auth_link.is_file():
                stderr.write(
                    "codexmgr codex: warning: Windows denied permission to link "
                    "global auth. Sign in to Codex for this project if prompted, "
                    "or enable Developer Mode in Windows Settings to allow symlinks.\n"
                )
                if stdin is not None and stdin.isatty() and stderr.isatty():
                    stderr.write("Press Enter to continue.\n")
                    stderr.flush()
                    stdin.readline()
    else:
        stderr.write(
            "codexmgr codex: warning: no global auth found at "
            f"{global_auth}; you may need to auth once.\n"
        )
    return environment


def _global_auth_path(environment: Mapping[str, str]) -> Path:
    """Resolve the read-only global authentication source.

    Args:
        environment: Launch environment with optional HOME and auth overrides.

    Returns:
        ``CODEX_GLOBAL_AUTH`` when non-empty, otherwise the Codex auth path under
        ``HOME`` or the platform's default user home.
    """
    configured_auth = environment.get("CODEX_GLOBAL_AUTH")
    if configured_auth:
        return Path(configured_auth)
    configured_home = environment.get("HOME")
    user_home = Path(configured_home) if configured_home else Path.home()
    return user_home / ".codex" / "auth.json"


def _replace_auth_link(auth_link: Path, global_auth: Path) -> None:
    """Replace the project auth entry with a link to global authentication.

    Args:
        auth_link: Project-local ``.codex/.runtime/auth.json`` link path.
        global_auth: Existing global authentication source file.

    Returns:
        None. Any existing file or symbolic link at ``auth_link`` is replaced
        after the new link is created.
    """
    with TemporaryDirectory(prefix=".auth-", dir=auth_link.parent) as staging_dir:
        staged_link = Path(staging_dir) / auth_link.name
        staged_link.symlink_to(global_auth)
        staged_link.replace(auth_link)
