"""Safety tests for managed-copy conflict snapshots and CLI resolutions."""

from pathlib import Path

import pytest

from codexmgr.core.errors import CommandError
from codexmgr.project.copy_conflicts import (
    CopyResolution,
    find_copy_conflicts,
    parse_copy_resolutions,
)
from codexmgr.project.copy_validation import prepare_source_updates
from codexmgr.skills.copies import SkillCopyFile


def test_noninteractive_resolution_rejects_abort_action(tmp_path: Path):
    """The CLI reserves abort for interactive choice flows."""
    with pytest.raises(CommandError, match="Unsupported copy resolution"):
        parse_copy_resolutions(tmp_path, [("target.md", "abort")])


def test_prepared_conflict_rejects_concurrent_target_change(tmp_path: Path):
    """A target changed after discovery is rejected before managed writes."""
    source = tmp_path / "source" / "SKILL.md"
    target = tmp_path / "project" / ".agents" / "skills" / "review" / "SKILL.md"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_bytes(b"source\n")
    target.write_bytes(b"local one\n")
    copy_file = SkillCopyFile(source, target, source.read_bytes())
    conflicts = find_copy_conflicts([copy_file])
    resolutions = {target.absolute(): CopyResolution.KEEP_LOCAL}
    target.write_bytes(b"local two\n")

    with pytest.raises(CommandError, match="target changed during apply"):
        prepare_source_updates(tmp_path / "project", conflicts, resolutions)


def test_prepared_conflict_rejects_concurrent_source_change(tmp_path: Path):
    """A source changed after state construction is rejected before writes."""
    source = tmp_path / "source" / "SKILL.md"
    target = tmp_path / "project" / ".agents" / "skills" / "review" / "SKILL.md"
    source.parent.mkdir(parents=True)
    target.parent.mkdir(parents=True)
    source.write_bytes(b"source one\n")
    target.write_bytes(b"local\n")
    copy_file = SkillCopyFile(source, target, source.read_bytes())
    conflicts = find_copy_conflicts([copy_file])
    resolutions = {target.absolute(): CopyResolution.OVERWRITE_LOCAL}
    source.write_bytes(b"source two\n")

    with pytest.raises(CommandError, match="source changed during apply"):
        prepare_source_updates(tmp_path / "project", conflicts, resolutions)
