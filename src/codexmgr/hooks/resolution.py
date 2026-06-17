"""Resolve project hook configuration into generated state."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import hook_lists
from .copies import (
    HookCopy,
    expected_hook_copy_files,
    has_hook_copy_files,
    hook_copy_lock_entries,
    obsolete_hook_copy_targets,
    validate_hook_copy_targets,
)
from .merge import (
    dump_hooks_json,
    empty_hooks_document,
    has_hook_handlers,
    load_hooks_json,
    managed_hook_config,
    merge_hook_configs,
    remove_managed_handlers,
)
from .sources import (
    project_hook_dir,
    project_hooks_json_path,
    resolve_hook_source,
)


@dataclass(frozen=True)
class HookResolution:
    """Resolved hook configuration state.

    Attributes:
        hooks_json: Expected hooks.json data, or None when no file should be written.
        remove_hooks_json: Whether a previous managed hooks.json should be removed.
        copies: Managed project-local hook copies.
        copy_files: Expected files inside managed hook copies.
        obsolete_copy_targets: Previous managed hook copy targets to remove.
        created_hooks_json: Whether the project hooks.json is codexmgr-created.
        enabled: Configured enabled hook bundle names.
        disabled: Configured disabled hook bundle names.
    """

    hooks_json: dict[str, Any] | None
    remove_hooks_json: bool
    copies: list[HookCopy]
    copy_files: list[Any]
    obsolete_copy_targets: list[Path]
    created_hooks_json: bool
    enabled: list[str]
    disabled: list[str]


def empty_hook_resolution() -> HookResolution:
    """Return an empty hook resolution for projects without hooks config.

    Returns:
        A resolved hook state with no generated hook outputs.
    """
    return HookResolution(None, False, [], [], [], False, [], [])


def resolve_project_hooks(
    project_config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> HookResolution:
    """Resolve configured hook bundles into generated config and copy state.

    Args:
        project_config: Parsed project codexmgr config.
        cwd: Project directory.
        codexmgr_home: codexmgr home directory.
        previous_lock: Previous codexmgr lock data.

    Returns:
        Resolved hook state.
    """
    enabled, disabled = hook_lists(project_config)
    existing = _load_existing_project_hooks(cwd)
    managed_configs, copies = _managed_hook_inputs(enabled, cwd, codexmgr_home)
    validate_hook_copy_targets(copies, previous_lock)

    unmanaged = remove_managed_handlers(existing)
    merged = merge_hook_configs(existing, managed_configs)
    created = _created_hooks_json(cwd, previous_lock)
    remove_hooks_json = _should_remove_hooks_json(enabled, unmanaged, created, cwd)
    hooks_json = None if remove_hooks_json else _expected_hooks_json(enabled, merged, unmanaged)
    return HookResolution(
        hooks_json,
        remove_hooks_json,
        copies,
        expected_hook_copy_files(copies),
        obsolete_hook_copy_targets(previous_lock, copies),
        _lock_created_hooks_json(created, hooks_json),
        enabled,
        disabled,
    )


def hooks_json_file(resolution: HookResolution, cwd: Path) -> tuple[Path, str] | None:
    """Build generated hooks.json file data for project apply.

    Args:
        resolution: Resolved hook state.
        cwd: Project directory.

    Returns:
        Path and JSON text when hooks.json should be written, otherwise None.
    """
    if resolution.hooks_json is None:
        return None
    return project_hooks_json_path(cwd), dump_hooks_json(resolution.hooks_json)


def hook_lock_data(resolution: HookResolution) -> dict[str, Any]:
    """Build lockfile data for configured hook bundles.

    Args:
        resolution: Resolved hook state.

    Returns:
        TOML-serializable lock data for hooks.
    """
    data: dict[str, Any] = {
        "enabled": resolution.enabled,
        "disabled": resolution.disabled,
    }
    if resolution.created_hooks_json:
        data["created_hooks_json"] = True
    copy_entries = hook_copy_lock_entries(resolution.copies)
    if copy_entries:
        data["copies"] = copy_entries
    return data


def _load_existing_project_hooks(cwd: Path) -> dict[str, Any]:
    """Load existing project hooks.json or return an empty document.

    Args:
        cwd: Project directory.

    Returns:
        Parsed project hook config.
    """
    path = project_hooks_json_path(cwd)
    if not path.exists():
        return empty_hooks_document()
    return load_hooks_json(path, require_hooks=False)


def _managed_hook_inputs(
    enabled: list[str],
    cwd: Path,
    codexmgr_home: Path,
) -> tuple[list[dict[str, Any]], list[HookCopy]]:
    """Build managed configs and copy plans for enabled hooks.

    Args:
        enabled: Configured enabled hook bundle names.
        cwd: Project directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Managed hook configs and copy plans.
    """
    configs: list[dict[str, Any]] = []
    copies: list[HookCopy] = []
    for name in enabled:
        source = resolve_hook_source(name, codexmgr_home)
        if source is None:
            continue
        source_config = load_hooks_json(source.config_file, require_hooks=True)
        configs.append(managed_hook_config(source_config, name))
        if has_hook_copy_files(source.hook_dir):
            copies.append(HookCopy(name, source.hook_dir, project_hook_dir(cwd, name)))
    return configs, copies


def _created_hooks_json(cwd: Path, previous_lock: Mapping[str, Any]) -> bool:
    """Return whether hooks.json should be considered codexmgr-created.

    Args:
        cwd: Project directory.
        previous_lock: Previous codexmgr lock data.

    Returns:
        True when hooks.json was created by codexmgr or does not yet exist.
    """
    previous_hooks = previous_lock.get("hooks", {})
    if isinstance(previous_hooks, Mapping) and previous_hooks.get("created_hooks_json"):
        return True
    return not project_hooks_json_path(cwd).exists()


def _should_remove_hooks_json(
    enabled: list[str],
    unmanaged: Mapping[str, Any],
    created: bool,
    cwd: Path,
) -> bool:
    """Return whether a previously managed hooks.json file should be deleted.

    Args:
        enabled: Configured enabled hook bundle names.
        unmanaged: Existing hook config after removing managed handlers.
        created: Whether hooks.json is considered codexmgr-created.
        cwd: Project directory.

    Returns:
        True when hooks.json exists and has no remaining unmanaged handlers.
    """
    return (
        not enabled
        and created
        and project_hooks_json_path(cwd).exists()
        and not has_hook_handlers(unmanaged)
    )


def _expected_hooks_json(
    enabled: list[str],
    merged: Mapping[str, Any],
    unmanaged: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return expected hooks.json content for the current hook state.

    Args:
        enabled: Configured enabled hook bundle names.
        merged: Existing unmanaged hooks plus current managed hooks.
        unmanaged: Existing hook config after removing managed handlers.

    Returns:
        Expected hooks.json data, or None when no file should be managed.
    """
    if enabled or has_hook_handlers(merged):
        return dict(merged)
    if has_hook_handlers(unmanaged):
        return dict(unmanaged)
    return None


def _lock_created_hooks_json(created: bool, hooks_json: Mapping[str, Any] | None) -> bool:
    """Return whether lock data should keep created-hooks-json ownership.

    Args:
        created: Whether the current hooks.json is codexmgr-created.
        hooks_json: Expected hooks.json data.

    Returns:
        True when hooks.json should remain tracked as codexmgr-created.
    """
    return created and hooks_json is not None
