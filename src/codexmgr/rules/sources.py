"""Resolve reusable rule references under CODEXMGR_HOME."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from ..core.errors import CommandError


@dataclass(frozen=True)
class RuleRef:
    """A canonical reusable rule reference.

    Attributes:
        value: Canonical POSIX-style relative reference.
        is_dir: Whether the reference points to a source directory.
    """

    value: str
    is_dir: bool


def rules_source_root(codexmgr_home):
    """Return the CODEXMGR_HOME rules source root.

    Args:
        codexmgr_home: Codexmgr home directory.

    Returns:
        Path to the reusable rules directory.
    """
    return codexmgr_home / "rules"


def project_rules_dir(cwd):
    """Return the project-local rules target directory.

    Args:
        cwd: Project directory.

    Returns:
        Path to the project `.rules` directory.
    """
    return cwd / ".rules"


def validate_rule_ref(ref: str) -> None:
    """Validate rule reference syntax.

    Args:
        ref: Candidate POSIX-style relative rule reference.

    Raises:
        CommandError: If the reference cannot be used safely.
    """
    if ref == "" or ref.strip() == "":
        raise CommandError("Invalid rule ref: empty")
    if "\\" in ref:
        raise CommandError(f"Invalid rule ref: {ref}")
    path = PurePosixPath(ref)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise CommandError(f"Invalid rule ref: {ref}")
    if any(part == "" for part in ref.split("/")[:-1]):
        raise CommandError(f"Invalid rule ref: {ref}")


def canonical_rule_ref(ref: str, codexmgr_home) -> RuleRef:
    """Resolve an existing rule reference to its canonical form.

    Args:
        ref: User-supplied rule reference.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Canonical rule reference.

    Raises:
        CommandError: If the ref is invalid or missing.
    """
    validate_rule_ref(ref)
    found = canonical_rule_ref_if_exists(ref, codexmgr_home)
    if found is None:
        raise CommandError(f"Rule not found: {rules_source_root(codexmgr_home) / ref}")
    return found


def canonical_rule_ref_if_exists(ref: str, codexmgr_home) -> RuleRef | None:
    """Resolve a rule ref only when the referenced source exists.

    Args:
        ref: User-supplied rule reference.
        codexmgr_home: Codexmgr home directory.

    Returns:
        Canonical reference, or None when no matching source exists.
    """
    validate_rule_ref(ref)
    root = rules_source_root(codexmgr_home)
    stripped = ref.rstrip("/")
    if ref.endswith("/"):
        return RuleRef(f"{stripped}/", True) if (root / stripped).is_dir() else None
    markdown = root / f"{ref}.md"
    if "." not in PurePosixPath(ref).name and markdown.is_file():
        return RuleRef(f"{ref}.md", False)
    exact = root / ref
    if exact.is_file():
        return RuleRef(ref, False)
    if exact.is_dir():
        return RuleRef(f"{ref}/", True)
    return None


def normalize_missing_rule_ref(ref: str) -> RuleRef:
    """Validate and normalize a missing disabled rule reference.

    Args:
        ref: User-supplied rule reference.

    Returns:
        Rule reference preserving the user's file or directory intent.
    """
    validate_rule_ref(ref)
    if ref.endswith("/"):
        return RuleRef(f"{ref.rstrip('/')}/", True)
    return RuleRef(ref, False)


def available_rule_refs(codexmgr_home) -> list[str]:
    """List all available source rule files and folders.

    Args:
        codexmgr_home: Codexmgr home directory.

    Returns:
        Sorted canonical rule references.
    """
    root = rules_source_root(codexmgr_home)
    if not root.is_dir():
        return []
    refs: list[str] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            refs.append(f"{relative}/")
        elif path.is_file():
            refs.append(relative)
    return refs
