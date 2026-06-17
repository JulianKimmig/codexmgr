"""Helpers for discovering named filesystem-backed codexmgr options."""

from pathlib import Path

from .errors import CommandError


def list_toml_options(directory: Path) -> list[str]:
    """List TOML-backed option names directly inside a directory.

    Args:
        directory: Directory containing one ``.toml`` file per named option.

    Returns:
        Sorted option names with the ``.toml`` suffix removed. Missing
        directories produce an empty list because they contain no installable
        options.
    """
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise CommandError(f"Option directory is not a directory: {directory}")
    return sorted(path.stem for path in directory.iterdir() if _is_toml_file(path))


def _is_toml_file(path: Path) -> bool:
    """Return whether a path is a direct TOML option file.

    Args:
        path: Candidate filesystem path from an options directory.

    Returns:
        True when the candidate is a regular file with a ``.toml`` suffix.
    """
    return path.is_file() and path.suffix == ".toml"
