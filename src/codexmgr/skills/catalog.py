"""Build skill-picker references while hiding owned project mirrors."""

from pathlib import Path

from ..core.paths import lock_path
from ..core.toml_io import load_optional_toml_file
from .copies import previous_skill_copies
from .sources import available_skill_names as store_skill_names


def available_skill_names(cwd: Path, codex_home: Path, codexmgr_home: Path) -> list[str]:
    """Return discoverable references without duplicate managed mirror rows.

    Args:
        cwd: Project root containing skill copies and their ownership lock.
        codex_home: Original Codex skill store.
        codexmgr_home: Manager source store for copied skills.

    Returns:
        Sorted references, retaining local copies when their source is absent.
    """
    names = set(store_skill_names(cwd, codex_home, codexmgr_home))
    previous = previous_skill_copies(
        load_optional_toml_file(lock_path(cwd)), cwd, codexmgr_home,
    )
    for copy in previous.values():
        reference = copy.source_path or copy.name
        if reference != copy.name and (copy.source / "SKILL.md").is_file():
            # A distinct real source may still legitimately use the flat name.
            if not any(
                (home / "skills" / copy.name / "SKILL.md").is_file()
                for home in (codex_home, codexmgr_home)
            ):
                names.discard(copy.name)
    return sorted(names)
