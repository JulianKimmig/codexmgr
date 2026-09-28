"""Discover exact guide references safely beneath the reusable document store."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..core.errors import CommandError


@dataclass(frozen=True)
class GuideRef:
    """One exact store-relative guide selection.

    Attributes:
        value: Canonical POSIX reference, ending in slash for directories.
        is_dir: Whether the reference selects a directory subtree.
    """

    value: str
    is_dir: bool


def guides_source_root(codexmgr_home: Path) -> Path:
    """Return the reusable document store.

    Args:
        codexmgr_home: Manager home containing reusable resources.

    Returns:
        Path to the source guides directory.
    """
    return codexmgr_home / "guides"


def project_guides_dir(cwd: Path) -> Path:
    """Return the managed document destination.

    Args:
        cwd: Current project root.

    Returns:
        Path to the project's guide directory.
    """
    return cwd / ".guides"


def validate_guide_ref(ref: str) -> None:
    """Reject non-relative or noncanonical refs before resolving filesystem paths.

    Args:
        ref: File or directory reference, optionally ending in one slash.

    Raises:
        CommandError: When the reference is unsafe or empty.
    """
    value = ref.removesuffix("/")
    if (
        not value.strip()
        or "\\" in value
        or "\x00" in value
        or PurePosixPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise CommandError(f"Invalid guide ref: {ref!r}")


def safe_guide_path(root: Path, ref: str) -> Path:
    """Return a validated child path without permitting symlink traversal.

    Args:
        root: Fixed guide source or destination root.
        ref: Validated store-relative file or folder reference.

    Returns:
        Child path, which need not exist yet.
    """
    validate_guide_ref(ref)
    path = root
    parts = ("", *PurePosixPath(ref).parts)
    for index, part in enumerate(parts):
        path = path / part
        if path.is_symlink():
            raise CommandError(f"Guide paths cannot traverse symlinks: {path}")
        if index < len(parts) - 1 and path.exists() and not path.is_dir():
            raise CommandError(f"Guide parent is not a directory: {path}")
    return path


def canonical_guide_ref_if_exists(ref: str, codexmgr_home: Path) -> GuideRef | None:
    """Resolve an exact file/folder reference, returning None when absent.

    Args:
        ref: Store-relative reference; no implicit filename extensions.
        codexmgr_home: Manager home containing the guide store.

    Returns:
        Canonical reference when its source exists.
    """
    path = safe_guide_path(guides_source_root(codexmgr_home), ref)
    if path.is_dir():
        return GuideRef(ref.rstrip("/") + "/", True)
    if not ref.endswith("/") and path.is_file():
        return GuideRef(ref, False)
    return None


def canonical_guide_ref(ref: str, codexmgr_home: Path) -> GuideRef:
    """Resolve an existing exact reference or raise an actionable source error.

    Args:
        ref: File or folder reference below the guide store.
        codexmgr_home: Manager home containing guides.

    Returns:
        Canonical reference to the existing source.
    """
    found = canonical_guide_ref_if_exists(ref, codexmgr_home)
    if found is None:
        raise CommandError(f"Guide not found: {guides_source_root(codexmgr_home) / ref}")
    return found


def normalize_missing_guide_ref(ref: str) -> GuideRef:
    """Preserve file/folder intent for a missing exclusion.

    Args:
        ref: Reference whose source is currently absent.

    Returns:
        Validated reference with directory intent indicated by its slash.
    """
    validate_guide_ref(ref)
    return GuideRef(ref, ref.endswith("/"))


def guide_descendants(root: Path, ref: str) -> list[Path]:
    """List sorted regular descendants while rejecting links and special files.

    Args:
        root: Fixed filesystem boundary containing guide documents.
        ref: Directory reference below that root, possibly absent before copying.

    Returns:
        Sorted descendant files and directories, without following symlinks.
    """
    directory = safe_guide_path(root, ref)
    paths = sorted(directory.rglob("*"))
    for path in paths:
        safe_guide_path(root, path.relative_to(root).as_posix())
        if not path.is_file() and not path.is_dir():
            raise CommandError(f"Guide source is not a regular file or directory: {path}")
    return paths


def available_guide_refs(codexmgr_home: Path) -> list[str]:
    """Discover selectable documents and folders.

    Args:
        codexmgr_home: Manager home containing the source guides directory.

    Returns:
        Sorted canonical references, or an empty list for an absent store.
    """
    root = guides_source_root(codexmgr_home)
    if root.is_symlink():
        raise CommandError(f"Guide paths cannot traverse symlinks: {root}")
    if not root.is_dir():
        return []
    refs = []
    for child in sorted(root.iterdir()):
        safe_guide_path(root, child.name)
        paths = [child, *guide_descendants(root, child.name)] if child.is_dir() else [child]
        for path in paths:
            if path.is_file() or path.is_dir():
                refs.append(path.relative_to(root).as_posix() + ("/" if path.is_dir() else ""))
    return sorted(refs)
