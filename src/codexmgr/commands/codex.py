"""Orchestration and subprocess execution for the external Codex command."""

import subprocess
from pathlib import Path
from typing import TextIO

from ..core.errors import CommandError
from .codex_jit import parse_codex_jit_request, run_with_jit_overlay
from .codex_launch import (
    build_project_codex_environment,
    parse_codex_launch_request,
)


def run_codex_command(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    codex_args: list[str],
    stderr: TextIO,
) -> int:
    """Select a launch mode and run the external Codex executable.

    Args:
        cwd: Project working directory for the external Codex process.
        codex_home: Codex home used to resolve project skills.
        codexmgr_home: codexmgr home containing package sources.
        codex_args: Raw arguments after ``codexmgr codex``.
        stderr: Stream that receives launch warnings.

    Returns:
        The external Codex process return code.
    """
    launch_request = parse_codex_launch_request(codex_args)
    if launch_request.simple:
        return run_codex(cwd, launch_request.codex_args)

    request = parse_codex_jit_request(launch_request.codex_args)

    def run_project_codex(project_cwd: Path, args: list[str]) -> int:
        """Launch Codex with the prepared project-local environment.

        Args:
            project_cwd: Project working directory for the child process.
            args: Arguments to proxy to the Codex executable.

        Returns:
            The external Codex process return code.
        """
        environment = build_project_codex_environment(project_cwd, stderr)
        return _run_subprocess(project_cwd, args, environment)

    if request.enabled:
        return run_with_jit_overlay(
            request,
            cwd,
            codex_home,
            codexmgr_home,
            run_project_codex,
        )
    from ..project.apply import apply_project_config

    apply_project_config(cwd, codex_home, codexmgr_home)
    return run_project_codex(cwd, launch_request.codex_args)


def run_codex(cwd: Path, codex_args: list[str]) -> int:
    """Run the basic external Codex command without project modifications.

    Args:
        cwd: Project working directory for the external codex process.
        codex_args: Arguments to pass through to codex.

    Returns:
        The external codex process return code.
    """
    return _run_subprocess(cwd, codex_args)


def build_codex_command(cwd: Path, codex_args: list[str]) -> list[str]:
    """Build an argument-preserving external Codex command invocation.

    Args:
        cwd: Project working directory, retained for the public helper contract.
        codex_args: Arguments to pass through to codex.

    Returns:
        The complete argv for the external codex process.
    """
    return ["codex", *codex_args]


def _run_subprocess(
    cwd: Path,
    codex_args: list[str],
    environment: dict[str, str] | None = None,
) -> int:
    """Run Codex and translate executable lookup failures.

    Args:
        cwd: Working directory for the external Codex process.
        codex_args: Arguments to pass through to Codex.
        environment: Optional explicit child process environment.

    Returns:
        The external Codex process return code.
    """
    command = build_codex_command(cwd, codex_args)
    try:
        if environment is None:
            return subprocess.run(command, cwd=cwd).returncode
        return subprocess.run(command, cwd=cwd, env=environment).returncode
    except FileNotFoundError as exc:
        raise CommandError("codex command not found") from exc
