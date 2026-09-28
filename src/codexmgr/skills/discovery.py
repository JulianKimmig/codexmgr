"""Discover grouped skill directories without descending into skill bundles."""

from pathlib import Path


def skill_paths(root: Path) -> list[str]:
    """Return sorted POSIX references below root, pruning skills and link cycles.

    Args:
        root: Skill store whose child directories should be searched.

    Returns:
        Relative directory references for each discovered SKILL.md file.
    """
    if not root.is_dir():
        return []
    found: list[str] = []
    pending = [(root, frozenset())]
    while pending:
        directory, ancestors = pending.pop()
        resolved = directory.resolve()
        if resolved in ancestors:
            continue
        if directory != root and (directory / "SKILL.md").is_file():
            found.append(directory.relative_to(root).as_posix())
            continue
        pending.extend(
            (child, ancestors | {resolved})
            for child in sorted(directory.iterdir())
            if child.is_dir()
        )
    return sorted(found)


def is_store_reference(reference: str) -> bool:
    """Return whether reference can identify a skill within a store.

    Args:
        reference: User-provided skill name, qualified name, or explicit path.

    Returns:
        True for safe bare or group-qualified directory references.
    """
    return (
        bool(reference)
        and not reference.startswith(("/", "~"))
        and "\\" not in reference
        and all(part not in {"", ".", ".."} for part in reference.split("/"))
        and Path(reference).name != "SKILL.md"
    )


def matching_paths(root: Path, reference: str) -> list[str]:
    """Return store paths matching a qualified reference or bare leaf name.

    Args:
        root: Skill store directory.
        reference: Requested skill reference.

    Returns:
        An exact relative match, otherwise matching leaf names. Explicit
        paths return an empty list.
    """
    if not is_store_reference(reference):
        return []
    paths = skill_paths(root)
    if reference in paths:
        return [reference]
    return [
        name for name in paths
        if name == reference or ("/" not in reference and Path(name).name == reference)
    ]
