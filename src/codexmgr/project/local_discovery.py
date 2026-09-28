"""Discover unowned local documents beneath selected Rules and Guides folders."""

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value
from ..guides.config import guide_lists
from ..guides.copies import previous_guide_copies
from ..guides.sources import canonical_guide_ref, canonical_guide_ref_if_exists
from ..rules.config import rule_lists
from ..rules.copies import previous_rule_copies
from ..rules.sources import canonical_rule_ref, canonical_rule_ref_if_exists
from .copy_conflicts import CopyConflict


def validate_document_ref(ref: str) -> None:
    """Require a canonical relative file identity before resolving local imports.

    Args:
        ref: POSIX path below the document source and target roots.

    Raises:
        CommandError: If the identity is empty, absolute, or traverses parents.
    """
    if (not ref.strip() or "\\" in ref or "\x00" in ref
            or PurePosixPath(ref).is_absolute() or Path(ref).anchor
            or any(part in {"", ".", ".."} for part in ref.split("/"))):
        raise CommandError(f"Invalid local document reference: {ref!r}")


def safe_document_path(root: Path, ref: str) -> Path:
    """Resolve a document child without following source or target links.

    Args:
        root: Fixed source or project resource boundary.
        ref: Relative document or directory identity without a trailing slash.

    Returns:
        Validated child path, whether or not it exists yet.
    """
    validate_document_ref(ref)
    parts = ("", *PurePosixPath(ref).parts)
    path = root
    for index, part in enumerate(parts):
        path /= part
        if path.is_symlink():
            raise CommandError(f"Local document paths cannot traverse symlinks: {path}")
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise CommandError(f"Local document parent is not a directory: {path}")
    return path


def project_only_refs(previous_lock: Mapping[str, Any], family: str) -> list[str]:
    """Read portable remembered project-only file decisions from the prior lock.

    Args:
        previous_lock: Previous project lock mapping.
        family: Either guides or rules.

    Returns:
        Sorted unique safe file references, never ownership entries.
    """
    table = previous_lock.get(family, {})
    if not isinstance(table, Mapping):
        raise CommandError(f"codexmgr.lock [{family}] must be a table")
    values = plain_toml_value(table.get("project_only", []))
    try:
        if not isinstance(values, list) or not all(isinstance(ref, str) for ref in values):
            raise CommandError("expected a list of file references")
        for ref in values:
            validate_document_ref(ref)
    except CommandError as exc:
        raise CommandError(f"Invalid codexmgr.lock {family}.project_only: {exc}") from exc
    return sorted(set(values))


def discover_local_imports(
    config: Mapping[str, Any], previous_lock: Mapping[str, Any],
    cwd: Path, codexmgr_home: Path,
) -> list[CopyConflict]:
    """Find new local files without existing sources or previous copy ownership.

    Args:
        config: Current staged or persisted project selections.
        previous_lock: Last applied ownership and remembered local-only choices.
        cwd: Project root containing document targets.
        codexmgr_home: Shared store receiving explicitly approved imports.

    Returns:
        Stable per-file decisions with absent source snapshots.
    """
    found: dict[Path, CopyConflict] = {}
    families = (
        ("guides", guide_lists, canonical_guide_ref, canonical_guide_ref_if_exists, previous_guide_copies),
        ("rules", rule_lists, canonical_rule_ref, canonical_rule_ref_if_exists, previous_rule_copies),
    )
    for family, lists, canonical, existing, previous in families:
        if family not in config:
            continue
        remembered = set(project_only_refs(previous_lock, family))
        owned = set(previous(previous_lock, cwd, codexmgr_home))
        enabled, disabled = lists(config)
        excluded = [(existing(ref, codexmgr_home).value if existing(ref, codexmgr_home) else ref)
                    for ref in disabled]
        source_root, target_root = codexmgr_home / family, cwd / f".{family}"
        for ref in enabled:
            selection = canonical(ref, codexmgr_home)
            if not selection.is_dir:
                continue
            folder = selection.value.rstrip("/")
            if _excluded(folder, excluded):
                continue
            directory = safe_document_path(target_root, folder)
            if not directory.exists():
                continue
            for relative in _local_files(target_root, folder, excluded):
                if relative in owned or relative in remembered:
                    continue
                source = safe_document_path(source_root, relative)
                if source.exists():
                    continue
                target = safe_document_path(target_root, relative)
                found[target] = CopyConflict(
                    source, target, None, target.read_bytes(), family[:-1],
                    source_root, target_root,
                )
    return sorted(found.values(), key=lambda item: str(item.target))


def _local_files(root: Path, folder: str, excluded: list[str]) -> list[str]:
    """Walk a selected subtree, pruning exclusions before reading any content.

    Args:
        root: Project document root.
        folder: Safe selected subdirectory relative to root.
        excluded: Canonical file/folder exclusions that always win.

    Returns:
        Regular local-file identities; links and special files fail explicitly.
    """
    files = []
    directory = safe_document_path(root, folder)
    if not directory.is_dir():
        raise CommandError(f"Local document folder is not a directory: {directory}")
    for path in sorted(directory.iterdir()):
        relative = path.relative_to(root).as_posix()
        if _excluded(relative, excluded):
            continue
        safe_document_path(root, relative)
        if path.is_dir():
            files.extend(_local_files(root, relative, excluded))
        elif path.is_file():
            files.append(relative)
        else:
            raise CommandError(f"Local document is not a regular file: {path}")
    return files


def _excluded(ref: str, excluded: list[str]) -> bool:
    """Return whether a file or folder ref is covered by an exclusion.

    Args:
        ref: Candidate path without a trailing slash.
        excluded: Canonical explicit exclusions.

    Returns:
        True for an exact exclusion or a disabled ancestor folder.
    """
    return any(ref == item.rstrip("/") or (item.endswith("/") and ref.startswith(item))
               for item in excluded)
