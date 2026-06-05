import os
from pathlib import Path

from .errors import CommandError


def global_codex_dir() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def project_codex_dir(cwd: Path) -> Path:
    return cwd / ".codex"


def config_path(cwd: Path) -> Path:
    return project_codex_dir(cwd) / "codexmgr.toml"


def lock_path(cwd: Path) -> Path:
    return project_codex_dir(cwd) / "codexmgr.lock"


def codex_config_path(cwd: Path) -> Path:
    return project_codex_dir(cwd) / "config.toml"


def agents_md_path(cwd: Path) -> Path:
    return cwd / "AGENTS.md"


def resolve_template(reference: str, cwd: Path, codex_home: Path) -> tuple[str, Path]:
    if _is_named_template(reference):
        source_id = reference
        path = codex_home / "agentsmd" / f"{reference}.toml"
    else:
        path = _expand_path(reference, cwd)
        source_id = path.stem

    if not path.is_file():
        raise CommandError(f"Template not found: {path}")

    return source_id, path


def _is_named_template(reference: str) -> bool:
    raw = reference.strip()
    return "/" not in raw and "\\" not in raw and not raw.endswith(".toml")


def _expand_path(reference: str, cwd: Path) -> Path:
    path = Path(reference).expanduser()
    if path.is_absolute():
        return path
    return cwd / path
