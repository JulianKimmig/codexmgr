"""Prepare portable ownership and safely publish explicitly approved local files."""

from dataclasses import replace
from pathlib import Path
import tomllib

from ..core.errors import CommandError
from ..core.paths import lock_path
from ..core.toml_io import dump_toml
from ..guides.copies import GuideCopy
from ..rules.copies import RuleCopy
from .copy_conflicts import CopyConflict, CopyResolution
from .local_discovery import safe_document_path
from .state import GeneratedFile, ProjectBuild


def validate_local_import(conflict: CopyConflict) -> None:
    """Recheck absent sources, path boundaries, and approved target bytes.

    Args:
        conflict: Candidate carrying source/target roots and discovery bytes.

    Raises:
        CommandError: If approval is stale or a path is unsafe.
    """
    if conflict.source_root is None or conflict.target_root is None:
        raise CommandError("Local import is missing its document boundaries")
    safe_document_path(conflict.source_root, conflict.source.relative_to(conflict.source_root).as_posix())
    safe_document_path(conflict.target_root, conflict.target.relative_to(conflict.target_root).as_posix())
    if conflict.source.exists():
        raise CommandError(f"Local import source appeared during apply: {conflict.source}")
    if not conflict.target.is_file() or conflict.target.read_bytes() != conflict.target_content:
        raise CommandError(f"Managed copy target changed during apply: {conflict.target}")


def publish_local_import(conflict: CopyConflict) -> None:
    """Create a shared source exclusively, without ever overwriting an existing file.

    Args:
        conflict: Approved and previously validated new local document.
    """
    validate_local_import(conflict)
    conflict.source.parent.mkdir(parents=True, exist_ok=True)
    try:
        with conflict.source.open("xb") as stream:
            stream.write(conflict.target_content)
    except FileExistsError as exc:
        raise CommandError(f"Local import source appeared during apply: {conflict.source}") from exc


def prepare_local_import_state(
    state: ProjectBuild, resolutions: dict[Path, CopyResolution], cwd: Path,
) -> ProjectBuild:
    """Build the post-decision lock and copy ownership without writing any file.

    Args:
        state: Original generated state and discovered local import candidates.
        resolutions: Validated actions keyed by absolute project target.
        cwd: Project root used to identify its generated lock file.

    Returns:
        State with approved imports owned and project-only decisions remembered.
    """
    if not state.local_imports:
        return state
    lock_file = next(file for file in state.files if file.path == lock_path(cwd))
    lock = tomllib.loads(lock_file.content)
    guides, rules = list(state.guide_copies), list(state.rule_copies)
    for candidate in state.local_imports:
        family = candidate.resource_kind + "s"
        relative = candidate.target.relative_to(candidate.target_root).as_posix()
        table = lock[family]
        action = resolutions[candidate.target.absolute()]
        if action == CopyResolution.KEEP_LOCAL:
            table["project_only"] = sorted(set([*table.get("project_only", []), relative]))
        elif action == CopyResolution.UPDATE_SOURCE:
            entries = table.setdefault("copies", [])
            entries.append({"relative_path": relative, "source": "codexmgr_home",
                            "target": f".{family}/{relative}"})
            entries.sort(key=lambda entry: entry["relative_path"])
            if family == "guides":
                guides.append(GuideCopy(relative, candidate.source, candidate.target))
            else:
                rules.append(RuleCopy(relative, candidate.source, candidate.target))
    files = [GeneratedFile(file.path, dump_toml(lock)) if file.path == lock_file.path else file
             for file in state.files]
    return replace(state, files=files, guide_copies=guides, rule_copies=rules)
