"""Just-in-time package/profile overlays for the codex command."""

from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..packages.mutation import (
    apply_package_entries_to_config,
    selected_entries_for_package,
)
from ..project.apply import (
    apply_project_config,
    apply_project_state,
    build_project_state_from_config,
)
from ..project.config import load_required_project_config
from ..project.snapshot import restore_snapshots, snapshot_paths
from ..project.state import ProjectBuild


@dataclass(frozen=True)
class CodexJitRequest:
    """Parsed just-in-time package/profile request.

    Attributes:
        enabled: Whether codexmgr JIT overlay syntax was present.
        packages: Package names to overlay.
        profiles: Package profile names to merge into every package.
        codex_args: Arguments to pass to the external codex executable.
    """

    enabled: bool
    packages: list[str]
    profiles: list[str]
    codex_args: list[str]


def parse_codex_jit_request(codex_args: list[str]) -> CodexJitRequest:
    """Parse codexmgr-specific JIT package/profile arguments.

    Args:
        codex_args: Raw arguments after ``codexmgr codex``.

    Returns:
        Parsed JIT request, or a disabled request when no JIT syntax is used.
    """
    if "--profile" not in codex_args and "--package" not in codex_args:
        return CodexJitRequest(False, [], [], list(codex_args))
    control_args, passthrough = _split_control_args(codex_args)
    packages, profiles = _parse_control_args(control_args)
    if not packages:
        raise CommandError("codex JIT profiles require at least one package")
    return CodexJitRequest(True, packages, profiles, passthrough)


def build_jit_project_state(
    base_config: MutableMapping[str, Any],
    request: CodexJitRequest,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> ProjectBuild:
    """Build generated state for an ephemeral JIT overlay.

    Args:
        base_config: Parsed project codexmgr.toml content.
        request: Parsed JIT request.
        cwd: Project directory.
        codex_home: Codex home used for skill resolution.
        codexmgr_home: codexmgr home containing package sources.

    Returns:
        Generated state for the overlaid configuration.
    """
    overlay = deepcopy(base_config)
    for package_name in request.packages:
        entries = selected_entries_for_package(
            package_name,
            codexmgr_home,
            request.profiles,
        )
        apply_package_entries_to_config(overlay, entries, enabled=True)
    return build_project_state_from_config(overlay, cwd, codex_home, codexmgr_home)


def run_with_jit_overlay(
    request: CodexJitRequest,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    run_codex,
) -> int:
    """Run Codex with temporary package/profile generated state.

    Args:
        request: Parsed JIT request.
        cwd: Project directory.
        codex_home: Codex home used for apply.
        codexmgr_home: codexmgr home containing package sources.
        run_codex: Callable that starts the external Codex process.

    Returns:
        External Codex process exit code.
    """
    apply_project_config(cwd, codex_home, codexmgr_home)
    base_config = load_required_project_config(cwd)
    overlay_state = build_jit_project_state(
        base_config,
        request,
        cwd,
        codex_home,
        codexmgr_home,
    )
    snapshots = snapshot_paths(_state_paths(overlay_state))
    apply_project_state(overlay_state)
    try:
        return run_codex(cwd, request.codex_args)
    finally:
        restore_snapshots(snapshots)


def _split_control_args(codex_args: list[str]) -> tuple[list[str], list[str]]:
    """Split JIT control args from pass-through Codex args.

    Args:
        codex_args: Raw arguments after ``codexmgr codex``.

    Returns:
        Control arguments and arguments after an optional ``--`` separator.
    """
    if "--" not in codex_args:
        return list(codex_args), []
    separator = codex_args.index("--")
    return codex_args[:separator], codex_args[separator + 1 :]


def _parse_control_args(control_args: list[str]) -> tuple[list[str], list[str]]:
    """Parse package and profile control arguments.

    Args:
        control_args: Arguments before the ``--`` pass-through separator.

    Returns:
        Package names and profile names.
    """
    packages: list[str] = []
    profiles: list[str] = []
    index = 0
    while index < len(control_args):
        token = control_args[index]
        if token == "--package":
            values, index = _collect_values(control_args, index + 1, token)
            packages.extend(values)
        elif token == "--profile":
            values, index = _collect_values(control_args, index + 1, token)
            profiles.extend(values)
        elif token.startswith("-"):
            raise CommandError(f"Unsupported codex JIT argument: {token}")
        else:
            packages.append(token)
            index += 1
    return packages, profiles


def _collect_values(
    args: list[str],
    start: int,
    option: str,
) -> tuple[list[str], int]:
    """Collect non-option values after one control option.

    Args:
        args: Control argument list.
        start: Index after the option token.
        option: Option name used in error messages.

    Returns:
        Collected values and the next unread index.
    """
    values: list[str] = []
    index = start
    while index < len(args) and not args[index].startswith("--"):
        if args[index].startswith("-"):
            raise CommandError(f"Unsupported codex JIT argument: {args[index]}")
        values.append(args[index])
        index += 1
    if not values:
        raise CommandError(f"{option} requires at least one value")
    return values, index


def _state_paths(state: ProjectBuild) -> list[Path]:
    """Return filesystem paths touched by a generated project state.

    Args:
        state: Generated state to apply temporarily.

    Returns:
        Paths that should be restored after the JIT run.
    """
    return [
        *(generated_file.path for generated_file in state.files),
        *(skill_copy.target for skill_copy in state.skill_copies),
        *(hook_copy.target for hook_copy in state.hook_copies),
        *state.obsolete_file_targets,
        *state.obsolete_skill_copy_targets,
        *state.obsolete_hook_copy_targets,
    ]
