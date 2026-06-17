"""JSON merge helpers for project-local Codex hooks.json files."""

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..core.errors import CommandError

META_KEY = "codexmanager_meta"
META_VERSION = 1


def load_hooks_json(path: Path, *, require_hooks: bool) -> dict[str, Any]:
    """Load and validate a Codex hooks.json document.

    Args:
        path: JSON file to read.
        require_hooks: Whether the top-level hooks object must be present.

    Returns:
        Parsed JSON object.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CommandError(f"{path} must contain a JSON object")
    validate_hooks_document(data, path, require_hooks=require_hooks)
    return data


def dump_hooks_json(data: Mapping[str, Any]) -> str:
    """Serialize hooks.json data deterministically.

    Args:
        data: Parsed hooks.json content.

    Returns:
        Pretty-printed JSON text with a trailing newline.
    """
    return json.dumps(data, indent=2) + "\n"


def validate_hooks_document(
    data: Mapping[str, Any],
    path: Path,
    *,
    require_hooks: bool,
) -> None:
    """Validate the hook event, matcher-group, and handler container shape.

    Args:
        data: Parsed hooks.json content.
        path: Source path used in validation errors.
        require_hooks: Whether the top-level hooks object must be present.
    """
    if "hooks" not in data:
        if require_hooks:
            raise CommandError(f"{path} must include a hooks object")
        return
    hooks = data["hooks"]
    if not isinstance(hooks, Mapping):
        raise CommandError(f"{path} hooks must be an object")
    for event, groups in hooks.items():
        _validate_event_groups(path, event, groups)


def merge_hook_configs(
    existing: Mapping[str, Any],
    managed_configs: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge managed hook configs into existing local hook config.

    Args:
        existing: Existing project hooks.json data.
        managed_configs: Managed hook configs with metadata already injected.

    Returns:
        Merged hooks.json data with stale managed handlers removed.
    """
    merged = remove_managed_handlers(existing)
    hooks = _ensure_hooks_object(merged)
    for managed_config in managed_configs:
        for event, groups in managed_config["hooks"].items():
            hooks.setdefault(event, []).extend(copy.deepcopy(groups))
    return merged


def managed_hook_config(source: Mapping[str, Any], name: str) -> dict[str, Any]:
    """Copy a source hook config and tag every handler as codexmgr-managed.

    Args:
        source: Source hook config loaded from CODEXMGR_HOME.
        name: Hook bundle name.

    Returns:
        Hook config with codexmanager_meta on each handler.
    """
    managed = copy.deepcopy(source)
    for groups in managed["hooks"].values():
        for group in groups:
            for handler in group["hooks"]:
                handler[META_KEY] = {
                    "managed": True,
                    "hook": name,
                    "version": META_VERSION,
                }
    return managed


def remove_managed_handlers(
    data: Mapping[str, Any],
    *,
    hook_name: str | None = None,
) -> dict[str, Any]:
    """Remove codexmgr-managed handlers from hook config data.

    Args:
        data: Existing hooks.json data.
        hook_name: Optional bundle name filter. When omitted, all managed
            handlers are removed.

    Returns:
        A copied hooks.json object with empty groups and events pruned.
    """
    stripped = copy.deepcopy(data)
    hooks = stripped.get("hooks", {})
    if not isinstance(hooks, dict):
        return stripped
    for event in list(hooks):
        kept_groups = _groups_without_managed_handlers(hooks[event], hook_name)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    return stripped


def has_hook_handlers(data: Mapping[str, Any]) -> bool:
    """Return whether a hooks.json object contains any hook handlers.

    Args:
        data: Parsed hooks.json data.

    Returns:
        True when at least one event has at least one handler.
    """
    hooks = data.get("hooks", {})
    if not isinstance(hooks, Mapping):
        return False
    return any(group.get("hooks") for groups in hooks.values() for group in groups)


def empty_hooks_document() -> dict[str, Any]:
    """Create an empty hooks.json document.

    Returns:
        A JSON-compatible hooks document.
    """
    return {"hooks": {}}


def _validate_event_groups(path: Path, event: str, groups: Any) -> None:
    """Validate matcher groups for one hook event.

    Args:
        path: Source path used in validation errors.
        event: Hook event name.
        groups: Candidate matcher-group list.
    """
    if not isinstance(groups, list):
        raise CommandError(f"{path} hooks.{event} must be a list")
    for index, group in enumerate(groups):
        if not isinstance(group, Mapping):
            raise CommandError(f"{path} hooks.{event}[{index}] must be an object")
        handlers = group.get("hooks")
        if not isinstance(handlers, list):
            raise CommandError(f"{path} hooks.{event}[{index}].hooks must be a list")
        _validate_handlers(path, event, index, handlers)


def _validate_handlers(path: Path, event: str, index: int, handlers: list[Any]) -> None:
    """Validate hook handlers for one matcher group.

    Args:
        path: Source path used in validation errors.
        event: Hook event name.
        index: Matcher-group index.
        handlers: Candidate hook handlers.
    """
    for handler_index, handler in enumerate(handlers):
        if not isinstance(handler, Mapping):
            raise CommandError(
                f"{path} hooks.{event}[{index}].hooks[{handler_index}] must be an object"
            )


def _ensure_hooks_object(data: dict[str, Any]) -> dict[str, Any]:
    """Return the mutable top-level hooks object, creating it when absent.

    Args:
        data: Mutable hooks.json object.

    Returns:
        Top-level hooks object.
    """
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise CommandError(".codex/hooks.json hooks must be an object")
    return hooks


def _groups_without_managed_handlers(groups: Any, hook_name: str | None) -> list[Any]:
    """Remove managed handlers from one event's matcher groups.

    Args:
        groups: Existing matcher groups.
        hook_name: Optional managed hook bundle name filter.

    Returns:
        Matcher groups that still contain handlers.
    """
    kept_groups: list[Any] = []
    for group in groups:
        kept_handlers = [
            handler
            for handler in group["hooks"]
            if not _is_managed_handler(handler, hook_name)
        ]
        if kept_handlers:
            kept_group = copy.deepcopy(group)
            kept_group["hooks"] = kept_handlers
            kept_groups.append(kept_group)
    return kept_groups


def _is_managed_handler(handler: Mapping[str, Any], hook_name: str | None) -> bool:
    """Return whether a handler is owned by codexmgr.

    Args:
        handler: Hook handler object.
        hook_name: Optional managed hook bundle name filter.

    Returns:
        True when handler metadata marks it as managed by codexmgr.
    """
    meta = handler.get(META_KEY)
    if not isinstance(meta, Mapping) or meta.get("managed") is not True:
        return False
    if hook_name is None:
        return True
    return meta.get("hook") == hook_name
