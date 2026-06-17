"""Selection value helpers for TUI package and profile rows."""

from dataclasses import dataclass
from urllib.parse import quote, unquote

PACKAGE_PREFIX = "package:"
PROFILE_PREFIX = "package-profile:"


@dataclass(frozen=True)
class PackageSelection:
    """Parsed package selection-list value.

    Attributes:
        kind: Either ``package`` or ``profile``.
        package: Package name.
        profile: Profile name when ``kind`` is ``profile``.
    """

    kind: str
    package: str
    profile: str = ""


def package_value(name: str) -> str:
    """Encode one package selection value.

    Args:
        name: Package name.

    Returns:
        Stable selection value for a package root row.
    """
    return f"{PACKAGE_PREFIX}{_encode(name)}"


def package_profile_value(name: str, profile: str) -> str:
    """Encode one package profile selection value.

    Args:
        name: Package name.
        profile: Profile name.

    Returns:
        Stable selection value for a package profile row.
    """
    return f"{PROFILE_PREFIX}{_encode(name)}:{_encode(profile)}"


def parse_package_value(value: str) -> PackageSelection:
    """Parse a package selection value from the TUI.

    Args:
        value: Selection value emitted by the package list.

    Returns:
        Parsed package selection. Unprefixed values are treated as legacy
        package root rows.
    """
    if value.startswith(PROFILE_PREFIX):
        raw_package, raw_profile = value.removeprefix(PROFILE_PREFIX).split(":", 1)
        return PackageSelection("profile", _decode(raw_package), _decode(raw_profile))
    if value.startswith(PACKAGE_PREFIX):
        return PackageSelection("package", _decode(value.removeprefix(PACKAGE_PREFIX)))
    return PackageSelection("package", value)


def _encode(value: str) -> str:
    """Percent-encode one value component.

    Args:
        value: Raw value component.

    Returns:
        Encoded value safe for colon-separated selection strings.
    """
    return quote(value, safe="")


def _decode(value: str) -> str:
    """Decode one encoded value component.

    Args:
        value: Encoded value component.

    Returns:
        Decoded value.
    """
    return unquote(value)
