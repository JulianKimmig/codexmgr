"""Allocate flat managed skill folders using progressively qualified names."""

from collections import Counter
from pathlib import Path

from ..core.errors import CommandError
from .copies import SkillCopy
from .sources import CODEXMGR_HOME_SOURCE, SkillSource


def copy_name(
    selected: SkillSource,
    sources: list[SkillSource],
    cwd: Path,
    previous: dict[str, SkillCopy],
) -> str:
    """Choose a stable flat folder, extending collisions with ancestor groups.

    Args:
        selected: Manager-home skill that will receive a project copy.
        sources: Discoverable sources with managed mirrors removed.
        cwd: Project root whose existing skill folders must be protected.
        previous: Lock-owned copies, keyed by their assigned folder name.

    Returns:
        Unique destination folder name for the selected source.

    Raises:
        CommandError: When every available group prefix still conflicts.
    """
    manager = {
        source.skill_dir.resolve(): source
        for source in sources if source.source_type == CODEXMGR_HOME_SOURCE
    }
    pinned = {
        copy.source.resolve(): copy.name
        for copy in previous.values() if copy.source.resolve() in manager
    }
    root = cwd / ".agents" / "skills"
    occupied = {path.name for path in root.iterdir()} if root.is_dir() else set()
    occupied -= set(pinned.values())
    parts = {path: source.name.split("/") for path, source in manager.items()}
    depths = {path: 1 for path in manager}
    while True:
        names = {
            path: pinned.get(path, "-".join(parts[path][-depths[path]:]))
            for path in manager
        }
        counts = Counter(names.values())
        expand = [
            path for path, name in names.items()
            if (counts[name] > 1 or name in occupied)
            and path not in pinned and depths[path] < len(parts[path])
        ]
        if not expand:
            break
        for path in expand:
            depths[path] += 1
    path = selected.skill_dir.resolve()
    name = names[path]
    if counts[name] > 1 or (name in occupied and len(parts[path]) > 1):
        raise CommandError(
            f"Cannot assign a unique skill copy name for {selected.name}: {name}. "
            "All group prefixes are exhausted; rename a conflicting source group."
        )
    return name
