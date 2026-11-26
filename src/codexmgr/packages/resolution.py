"""Expand package sections into ordered resources from the manager store."""

from pathlib import Path

from ..core.errors import CommandError
from .config import (
    PackageConfig, PackageEntries, load_package_config, merge_package_resources,
    root_package_entries,
)
from .sources import require_package_config


class PackageResolver:
    """Resolve package sections using a manifest cache scoped to one operation."""

    def __init__(self, codexmgr_home: Path) -> None:
        """Initialize an empty cache for the given manager source directory."""
        self.home = codexmgr_home
        self._manifests: dict[Path, PackageConfig] = {}

    def section(self, name: str, profile: str | None = None) -> PackageEntries:
        """Resolve a package root or a single profile, including child package roots.

        Args:
            name: Bare package name.
            profile: Profile name, or None to select the root.

        Returns:
            Ordered resource entries for the requested section.
        """
        path, package = self._load(name)
        entries = root_package_entries(package) if profile is None else package.profiles.get(profile)
        if entries is None:
            raise CommandError(f"Package profile not found: {name}.{profile}")
        label = name if profile is None else f"{name}.{profile}"
        sections = [entries]
        active = {path}
        seen = {path}
        stack = [(path, label, iter(entries.packages))]
        while stack:
            _, _, includes = stack[-1]
            child = next(includes, None)
            if child is None:
                finished, _, _ = stack.pop()
                active.remove(finished)
                continue
            try:
                child_path, child_config = self._load(child)
            except CommandError as exc:
                chain = " -> ".join([*(item[1] for item in stack), child])
                raise CommandError(f"Package include {chain}: {exc}") from exc
            if child_path in active:
                chain = " -> ".join([*(item[1] for item in stack), child])
                raise CommandError(f"Package include cycle: {chain}")
            if child_path in seen:
                continue
            seen.add(child_path)
            active.add(child_path)
            child_entries = root_package_entries(child_config)
            sections.append(child_entries)
            stack.append((child_path, child, iter(child_entries.packages)))
        return merge_package_resources(sections)

    def _load(self, name: str) -> tuple[Path, PackageConfig]:
        """Return the canonical manifest path and its parsed content for a package."""
        path = require_package_config(name, self.home).resolve()
        if path not in self._manifests:
            self._manifests[path] = load_package_config(name, self.home)
        return path, self._manifests[path]
