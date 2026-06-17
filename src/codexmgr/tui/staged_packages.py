"""Package-related methods mixed into staged TUI configuration."""

from . import package_state as packages


class PackageStageMixin:
    """Methods for package and profile staged mutations."""

    def set_package_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable all entries from a packaged configuration.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            enabled: Whether package entries should be active.
        """
        packages.set_package_enabled(
            self.config,
            name,
            enabled,
            self.cwd,
            self.codexmgr_home,
        )

    def set_package_profile_enabled(
        self,
        name: str,
        profile: str,
        enabled: bool,
    ) -> None:
        """Enable or disable one package profile entry set.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            profile: Profile name within the package config.
            enabled: Whether profile entries should be active.
        """
        packages.set_package_profile_enabled(
            self.config,
            name,
            profile,
            enabled,
            self.cwd,
            self.codexmgr_home,
        )

    def set_package_available(self, name: str) -> None:
        """Clear root package entries from staged config.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
        """
        packages.set_package_available(
            self.config,
            name,
            self.cwd,
            self.codexmgr_home,
        )

    def set_package_profile_available(self, name: str, profile: str) -> None:
        """Clear package profile entries from staged config.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            profile: Profile name within the package config.
        """
        packages.set_package_profile_available(
            self.config,
            name,
            profile,
            self.codexmgr_home,
        )

    def package_state(self, name: str) -> str:
        """Return enabled, partial, or disabled for a package.

        Args:
            name: Package name under CODEXMGR_HOME/packages.

        Returns:
            Package state computed from staged entries.
        """
        return packages.package_state(self.config, name, self.codexmgr_home)

    def package_profile_state(self, name: str, profile: str) -> str:
        """Return enabled, partial, or disabled for a package profile.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            profile: Profile name within the package config.

        Returns:
            Package profile state computed from staged entries.
        """
        return packages.package_profile_state(
            self.config,
            name,
            profile,
            self.codexmgr_home,
        )
