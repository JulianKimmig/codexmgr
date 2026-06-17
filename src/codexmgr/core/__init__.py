"""Shared errors, path helpers, option discovery, and TOML utilities."""

from .errors import CommandError
from .options import list_toml_options
from .paths import (
    agents_md_path,
    codex_config_path,
    config_path,
    global_codex_dir,
    global_codexmgr_dir,
    lock_path,
    project_codex_dir,
    resolve_template,
)
from .toml_io import (
    dump_toml,
    ensure_toml_table,
    format_toml_value,
    load_optional_toml_file,
    load_toml_file,
    new_toml_table,
    plain_toml_value,
    write_toml_file,
)

__all__ = [
    "CommandError",
    "agents_md_path",
    "codex_config_path",
    "config_path",
    "dump_toml",
    "ensure_toml_table",
    "format_toml_value",
    "global_codex_dir",
    "global_codexmgr_dir",
    "list_toml_options",
    "load_optional_toml_file",
    "load_toml_file",
    "lock_path",
    "new_toml_table",
    "plain_toml_value",
    "project_codex_dir",
    "resolve_template",
    "write_toml_file",
]
