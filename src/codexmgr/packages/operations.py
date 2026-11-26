"""Apply package selections while protecting resources used by other selections."""

from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ..guides.config import guide_lists
from ..guides.sources import canonical_guide_ref_if_exists, normalize_missing_guide_ref
from ..mcp.project import mcp_source_names
from ..mcp.sources import load_mcp_sources
from ..rules.config import rule_lists
from ..rules.sources import canonical_rule_ref_if_exists, normalize_missing_rule_ref
from ..skills.groups import skill_selection_refs
from .config import RESOURCE_KEYS, PackageEntries, merge_package_resources
from .entries import apply_package_entries, remove_package_refs, validate_package_enable
from .resolution import PackageResolver
from .selections import (
    SELECTIONS_KEY, Selection, read_package_selections, selection_key, write_package_selections,
)

_FOLDERS = {
    "rules": (rule_lists, canonical_rule_ref_if_exists, normalize_missing_rule_ref),
    "guides": (guide_lists, canonical_guide_ref_if_exists, normalize_missing_guide_ref),
}


@dataclass(frozen=True)
class PackageWorkspace:
    """Project and home paths used to resolve package resources.

    Attributes:
        cwd: Project directory.
        codex_home: Codex skill source directory.
        codexmgr_home: Manager source directory.
    """

    cwd: Path
    codex_home: Path
    codexmgr_home: Path

    def resource_refs(self, entries: PackageEntries, config: Mapping[str, Any]) -> PackageEntries:
        """Expand skills and normalize folder selectors against the given project config.

        Returns:
            Resource references suitable for recording or comparison.
        """
        skills = self.skill_refs(entries, config)
        folders = {
            family: list(dict.fromkeys(self.folder_ref(family, ref) for ref in getattr(entries, family)))
            for family in _FOLDERS
        }
        return replace(entries, skills=list(skills.values()), **folders)

    def skill_refs(self, entries: PackageEntries, config: Mapping[str, Any]) -> dict[str, str]:
        """Return canonical skill identities and their applied spellings."""
        selected, _ = skill_selection_refs(
            entries.skills, config, self.cwd, self.codex_home, self.codexmgr_home,
        )
        return selected

    def folder_ref(self, family: str, ref: str) -> str:
        """Return the canonical selector for a rule or guide reference, even if missing."""
        _, present, missing = _FOLDERS[family]
        return (present(ref, self.codexmgr_home) or missing(ref)).value


def update_package_selections(
    config: MutableMapping[str, Any],
    requested: list[Selection],
    workspace: PackageWorkspace,
    *,
    state: str,
) -> None:
    """Update explicit selection records and eligible resource states as one staged change.

    Args:
        config: Live or staged project configuration to update on success.
        requested: Root and profile selections to update, in application order.
        workspace: Locations for package and resource lookup.
        state: Enabled, disabled, or available.
    """
    working = deepcopy(config)
    saved = read_package_selections(working)
    resolver = PackageResolver(workspace.codexmgr_home)
    selections: dict[Selection, PackageEntries] = {}
    for name, profile in requested:
        key = selection_key(name, profile)
        if key not in selections:
            selections[key] = (
                resolver.section(name, profile) if state == "enabled" or key not in saved
                else saved[key]
            )
    combined = merge_package_resources(selections.values())
    if state == "enabled":
        validate_package_enable(combined, workspace.cwd, workspace.codexmgr_home)
        applied_skills = workspace.skill_refs(combined, working)
        for selection, entries in selections.items():
            refs = workspace.resource_refs(entries, working)
            previous = saved.get(selection)
            saved[selection] = merge_package_resources((previous, refs)) if previous is not None else refs
        if applied_skills:
            # The resource mutator may replace a bare alias with a qualified
            # reference. Record the applied spelling for every affected owner.
            for selection, entries in saved.items():
                skills = workspace.skill_refs(entries, working)
                saved[selection] = replace(
                    entries, skills=[applied_skills.get(key, ref) for key, ref in skills.items()],
                )
    else:
        for selection in selections:
            saved.pop(selection, None)
        protected = merge_package_resources(saved.values())
        combined = _removable_resources(working, combined, protected, workspace, state)
    apply_package_entries(
        working, combined, workspace.codexmgr_home, state=state,
        cwd=workspace.cwd, codex_home=workspace.codex_home,
    )
    if combined.mcp:
        load_mcp_sources(mcp_source_names(working), workspace.codexmgr_home)
    write_package_selections(working, saved)
    config.update(working)
    if SELECTIONS_KEY not in working:
        config.pop(SELECTIONS_KEY, None)


def package_selection_display_entries(
    config: Mapping[str, Any], selection: Selection, workspace: PackageWorkspace,
) -> PackageEntries:
    """Return a row's entries, excluding inherited resources for an unselected row.

    Args:
        config: Staged project configuration.
        selection: Package root or profile row to display.
        workspace: Locations for package and resource lookup.

    Returns:
        Resource references to use for computing selectable state.
    """
    entries = workspace.resource_refs(PackageResolver(workspace.codexmgr_home).section(*selection), config)
    saved = read_package_selections(config)
    if selection_key(*selection) in saved or not saved:
        return entries
    protected = merge_package_resources(saved.values())
    return _without_protected(entries, protected, config, workspace, covered_folders=True)


def _without_protected(
    entries: PackageEntries, protected: PackageEntries, config: Mapping[str, Any],
    workspace: PackageWorkspace, *, covered_folders: bool = False,
) -> PackageEntries:
    """Filter exact protected resources and optionally inherited folder selectors."""
    refs = {
        family: [ref for ref in getattr(entries, family) if ref not in getattr(protected, family)]
        for family in RESOURCE_KEYS if family != "skills"
    }
    protected_skills = workspace.skill_refs(protected, config)
    # Keep group tokens when they are wholly unshared so the normal mutator also
    # clears any legacy literal group token.
    skills = workspace.skill_refs(entries, config)
    if skills.keys() & protected_skills.keys():
        refs["skills"] = [ref for key, ref in skills.items() if key not in protected_skills]
    else:
        refs["skills"] = entries.skills
    if covered_folders:
        for family in _FOLDERS:
            refs[family] = [
                ref for ref in refs[family]
                if not any(_covers(owner, ref) for owner in getattr(protected, family))
            ]
    return PackageEntries(**refs)


def _removable_resources(
    config: MutableMapping[str, Any], entries: PackageEntries, protected: PackageEntries,
    workspace: PackageWorkspace, state: str,
) -> PackageEntries:
    """Return unshared references and clear any folder selectors that overlap retained paths."""
    # Skill groups are left for the usual state mutator to expand when possible.
    folders = {
        family: list(dict.fromkeys(workspace.folder_ref(family, ref) for ref in getattr(entries, family)))
        for family in _FOLDERS
    }
    remaining = _without_protected(replace(entries, **folders), protected, config, workspace)
    for family, (read_lists, _, _) in _FOLDERS.items():
        candidates = getattr(remaining, family)
        overlaps = {
            ref for ref in candidates
            if any(
                _covers(ref, owner) or _covers(owner, ref)
                for owner in getattr(protected, family)
            )
        }
        # Remove the released selector so its unshared paths go away. A disable
        # exclusion would also mask retained paths under the same directory.
        if overlaps or state == "available" and candidates:
            to_clear = overlaps if state == "disabled" else set(candidates)
            enabled, disabled = read_lists(config)
            config_refs = enabled if state == "disabled" else [*enabled, *disabled]
            remove_package_refs(
                config, family,
                [ref for ref in config_refs if workspace.folder_ref(family, ref) in to_clear],
                enabled_only=state == "disabled",
            )
            candidates = [ref for ref in candidates if ref not in to_clear]
        folders[family] = candidates
    return replace(remaining, **folders)


def _covers(folder: str, ref: str) -> bool:
    """Return whether a directory selector can contribute the given resource."""
    return folder.endswith("/") and ref.startswith(folder)
