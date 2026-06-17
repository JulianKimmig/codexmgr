"""Managed Codex hook bundle support for codexmgr."""

from .config import disable_hook, enable_hook, hook_lists
from .listing import configured_hook_lists, hook_list_lines, missing_enabled_hooks
from .resolution import (
    HookResolution,
    empty_hook_resolution,
    hook_lock_data,
    hooks_json_file,
    resolve_project_hooks,
)

__all__ = [
    "HookResolution",
    "configured_hook_lists",
    "disable_hook",
    "empty_hook_resolution",
    "enable_hook",
    "hook_list_lines",
    "hook_lists",
    "hook_lock_data",
    "hooks_json_file",
    "missing_enabled_hooks",
    "resolve_project_hooks",
]
