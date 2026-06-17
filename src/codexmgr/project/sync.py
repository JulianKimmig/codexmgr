"""Generated-file sync checking for codexmgr projects."""

from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from typing import TextIO

from .apply import GeneratedFile, build_project_state
from ..skills.copies import SkillCopyFile


@dataclass(frozen=True)
class FileDiff:
    """Difference between a generated file on disk and expected content.

    Attributes:
        path: Filesystem path to the generated file.
        relative_path: Project-relative display path.
        current_exists: Whether the generated file currently exists.
        current: Current file content, or an empty string when missing.
        expected: Expected generated file content.
        binary: Whether either side could not be decoded as UTF-8 text.
    """

    path: Path
    relative_path: str
    current_exists: bool
    current: str
    expected: str
    binary: bool = False


def generated_file_diffs(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> list[FileDiff]:
    """Return generated files whose current content differs from expected.

    Args:
        cwd: Project directory whose generated files should be checked.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve AGENTS.md templates.

    Returns:
        File differences for all out-of-sync generated outputs.
    """
    diffs: list[FileDiff] = []
    state = build_project_state(cwd, codex_home, codexmgr_home)
    for generated_file in state.files:
        diff = _text_file_diff(cwd, generated_file)
        if diff is not None:
            diffs.append(diff)
    for copy_file in state.copy_files:
        diff = _copy_file_diff(cwd, copy_file)
        if diff is not None:
            diffs.append(diff)
    return diffs


def check_project_sync(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
    *,
    show_diff: bool,
) -> int:
    """Check generated files and write a command-line report.

    Args:
        cwd: Project directory whose generated files should be checked.
        codex_home: Global Codex home used to resolve named skills.
        codexmgr_home: codexmgr home used to resolve AGENTS.md templates.
        stdout: Stream for the check report.
        show_diff: Whether to print unified diffs instead of path summaries.

    Returns:
        Zero when generated files are in sync, one when differences are found.
    """
    diffs = generated_file_diffs(cwd, codex_home, codexmgr_home)
    if not diffs:
        stdout.write("Project Codex configuration is in sync\n")
        return 0
    if show_diff:
        stdout.write("".join(line for diff in diffs for line in _format_diff(diff)))
    else:
        for diff in diffs:
            stdout.write(f"Out of sync: {diff.relative_path}\n")
    return 1


def _format_diff(diff: FileDiff) -> list[str]:
    """Format one generated-file difference as a unified diff.

    Args:
        diff: File difference to format.

    Returns:
        Unified diff lines preserving line endings.
    """
    if diff.binary:
        return [
            f"--- {diff.relative_path} (current)\n",
            f"+++ {diff.relative_path} (expected)\n",
            "Binary files differ\n",
        ]
    lines = list(
        unified_diff(
            diff.current.splitlines(keepends=True),
            diff.expected.splitlines(keepends=True),
            fromfile=f"{diff.relative_path} (current)",
            tofile=f"{diff.relative_path} (expected)",
        )
    )
    if lines or diff.current_exists:
        return lines
    return [
        f"--- {diff.relative_path} (current)\n",
        f"+++ {diff.relative_path} (expected)\n",
    ]


def _text_file_diff(cwd: Path, generated_file: GeneratedFile) -> FileDiff | None:
    """Build a diff for one generated text file.

    Args:
        cwd: Project directory used as display root.
        generated_file: Expected generated text file.

    Returns:
        File diff, or None when current content matches.
    """
    current_exists = generated_file.path.exists()
    current = _read_existing_text(generated_file.path)
    if current_exists and current == generated_file.content:
        return None
    return FileDiff(
        generated_file.path,
        _display_path(cwd, generated_file.path),
        current_exists,
        current,
        generated_file.content,
    )


def _copy_file_diff(cwd: Path, copy_file: SkillCopyFile) -> FileDiff | None:
    """Build a diff for one managed skill-copy file.

    Args:
        cwd: Project directory used as display root.
        copy_file: Expected managed copy file.

    Returns:
        File diff, or None when current bytes match.
    """
    current_exists = copy_file.path.exists()
    current = copy_file.path.read_bytes() if current_exists else b""
    if current_exists and current == copy_file.content:
        return None
    current_text, current_binary = _decode_bytes(current)
    expected_text, expected_binary = _decode_bytes(copy_file.content)
    return FileDiff(
        copy_file.path,
        _display_path(cwd, copy_file.path),
        current_exists,
        current_text,
        expected_text,
        current_binary or expected_binary,
    )


def _decode_bytes(content: bytes) -> tuple[str, bool]:
    """Decode file bytes for diff display.

    Args:
        content: File bytes.

    Returns:
        Text content and whether decoding failed.
    """
    try:
        return content.decode("utf-8"), False
    except UnicodeDecodeError:
        return "", True


def _read_existing_text(path: Path) -> str:
    """Read existing generated file text or return an empty string.

    Args:
        path: File path to read.

    Returns:
        Current UTF-8 file content, or an empty string when missing.
    """
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _display_path(cwd: Path, path: Path) -> str:
    """Return a stable project-relative display path.

    Args:
        cwd: Project directory used as the display root.
        path: File path to display.

    Returns:
        POSIX-style project-relative path where possible.
    """
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return str(path)
