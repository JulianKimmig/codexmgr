"""CLI tests for provenance-aware managed-copy conflict resolution."""

import io
import json
from pathlib import Path

from codexmgr.interface.cli import main


def test_noninteractive_apply_reports_conflict_without_writing(
    workspace,
    run_cli_with_homes,
):
    """An unresolved managed-copy conflict leaves source and target unchanged."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    local_content = _skill_text("review", "# Local edit\n")
    target.write_text(local_content, encoding="utf-8")
    source_content = source.read_text(encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Managed copy conflict" in stderr
    assert ".agents/skills/review/SKILL.md" in stderr
    assert "--resolve .agents/skills/review/SKILL.md" in stderr
    assert source.read_text(encoding="utf-8") == source_content
    assert target.read_text(encoding="utf-8") == local_content


def test_keep_local_skips_one_apply_and_conflicts_again_next_time(
    workspace,
    run_cli_with_homes,
):
    """The keep-local resolution is temporary and never changes the source."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    local_content = _skill_text("review", "# Local edit\n")
    target.write_text(local_content, encoding="utf-8")
    source_content = source.read_text(encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".agents/skills/review/SKILL.md",
            "keep-local",
        ],
        project,
        codex_home,
        codexmgr_home,
    )
    next_exit, _, next_stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stdout == "Applied project Codex configuration\n"
    assert stderr == ""
    assert target.read_text(encoding="utf-8") == local_content
    assert source.read_text(encoding="utf-8") == source_content
    assert next_exit == 1
    assert "Managed copy conflict" in next_stderr


def test_overwrite_local_refreshes_the_managed_target(
    workspace,
    run_cli_with_homes,
):
    """The overwrite-local resolution copies canonical source bytes to target."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    target.write_text(_skill_text("review", "# Local edit\n"), encoding="utf-8")

    exit_code, _, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            str(target),
            "overwrite-local",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert target.read_bytes() == source.read_bytes()


def test_update_source_persists_valid_local_skill_content(
    workspace,
    run_cli_with_homes,
):
    """The update-source resolution promotes valid local skill bytes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    local_content = _skill_text("review", "# Improved locally\n")
    target.write_text(local_content, encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".agents/skills/review/SKILL.md",
            "update-source",
        ],
        project,
        codex_home,
        codexmgr_home,
    )
    check_exit, _, check_stderr = run_cli_with_homes(
        ["apply", "--check"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert "shared source" in stdout.lower()
    assert stderr == ""
    assert source.read_text(encoding="utf-8") == local_content
    assert target.read_text(encoding="utf-8") == local_content
    assert check_exit == 0
    assert check_stderr == ""


def test_update_source_rejects_invalid_local_skill_without_writing(
    workspace,
    run_cli_with_homes,
):
    """Invalid local skill metadata cannot replace the canonical source."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    source_content = source.read_text(encoding="utf-8")
    target.write_text("# Missing frontmatter\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".agents/skills/review/SKILL.md",
            "update-source",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "frontmatter" in stderr.lower()
    assert source.read_text(encoding="utf-8") == source_content
    assert target.read_text(encoding="utf-8") == "# Missing frontmatter\n"


def test_all_conflicts_are_resolved_before_any_copy_is_written(
    workspace,
    run_cli_with_homes,
):
    """A partially resolved invocation does not apply an earlier resolution."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    first_source, first_target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
        name="review",
    )
    _, second_target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
        name="audit",
        setup=False,
    )
    first_local = _skill_text("review", "# First local\n")
    second_local = _skill_text("audit", "# Second local\n")
    first_target.write_text(first_local, encoding="utf-8")
    second_target.write_text(second_local, encoding="utf-8")

    exit_code, _, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".agents/skills/review/SKILL.md",
            "overwrite-local",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert ".agents/skills/audit/SKILL.md" in stderr
    assert first_target.read_text(encoding="utf-8") == first_local
    assert first_target.read_bytes() != first_source.read_bytes()
    assert second_target.read_text(encoding="utf-8") == second_local


def test_interactive_abort_leaves_the_conflict_unchanged(
    workspace,
    run_cli_with_homes,
):
    """An interactive abort cancels apply before source or target writes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source, target = _enable_skill(
        project,
        codex_home,
        codexmgr_home,
        run_cli_with_homes,
    )
    source_content = source.read_text(encoding="utf-8")
    local_content = _skill_text("review", "# Local edit\n")
    target.write_text(local_content, encoding="utf-8")
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main(
        ["apply"],
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        stdin=_InteractiveInput("a\n"),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert "[a]bort" in stdout.getvalue()
    assert "aborted" in stderr.getvalue().lower()
    assert source.read_text(encoding="utf-8") == source_content
    assert target.read_text(encoding="utf-8") == local_content


def test_apply_resolves_agent_rule_and_hook_support_conflicts(
    workspace,
    run_cli_with_homes,
):
    """All source-backed resource families use the same target-level actions."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    agent_source = codexmgr_home / "agents" / "reviewer.toml"
    agent_source.parent.mkdir(parents=True)
    agent_source.write_text('name = "canonical"\n', encoding="utf-8")
    rule_source = codexmgr_home / "rules" / "python" / "testing.md"
    rule_source.parent.mkdir(parents=True)
    rule_source.write_text("# Canonical rule\n", encoding="utf-8")
    hook_dir = codexmgr_home / "hooks" / "audit"
    hook_dir.mkdir(parents=True)
    (hook_dir / "hooks.json").write_text(
        json.dumps({"hooks": {}}),
        encoding="utf-8",
    )
    hook_source = hook_dir / "audit.py"
    hook_source.write_text("print('canonical')\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["agents", "enable", "reviewer"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["rules", "enable", "python/testing.md"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["hooks", "enable", "audit"],
        project,
        codex_home,
        codexmgr_home,
    )
    agent_target = project / ".codex" / "agents" / "reviewer.toml"
    rule_target = project / ".rules" / "python" / "testing.md"
    hook_target = project / ".codex" / "hooks" / "audit" / "audit.py"
    agent_target.write_text('name = "local"\n', encoding="utf-8")
    rule_target.write_text("# Local rule\n", encoding="utf-8")
    hook_target.write_text("print('local')\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".codex/agents/reviewer.toml",
            "update-source",
            "--resolve",
            ".rules/python/testing.md",
            "keep-local",
            "--resolve",
            ".codex/hooks/audit/audit.py",
            "overwrite-local",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "shared source" in stdout.lower()
    assert agent_source.read_text(encoding="utf-8") == 'name = "local"\n'
    assert agent_target.read_text(encoding="utf-8") == 'name = "local"\n'
    assert rule_source.read_text(encoding="utf-8") == "# Canonical rule\n"
    assert rule_target.read_text(encoding="utf-8") == "# Local rule\n"
    assert hook_target.read_bytes() == hook_source.read_bytes()


def test_resolution_for_non_conflicting_target_is_rejected(
    workspace,
    run_cli_with_homes,
):
    """A stale or mistyped target resolution cannot silently affect apply."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _enable_skill(project, codex_home, codexmgr_home, run_cli_with_homes)

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "apply",
            "--resolve",
            ".agents/skills/review/missing.md",
            "keep-local",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "not a current copy conflict" in stderr


def _enable_skill(
    project: Path,
    codex_home: Path,
    codexmgr_home: Path,
    run_cli_with_homes,
    *,
    name: str = "review",
    setup: bool = True,
) -> tuple[Path, Path]:
    """Create and enable one manager-home skill.

    Args:
        project: Project directory receiving the managed copy.
        codex_home: Codex home passed to the CLI.
        codexmgr_home: Manager home containing the canonical skill.
        run_cli_with_homes: Test CLI helper fixture.
        name: Skill name to create and enable.
        setup: Whether to initialize the project before enabling the skill.

    Returns:
        Canonical source and managed target ``SKILL.md`` paths.
    """
    source = codexmgr_home / "skills" / name / "SKILL.md"
    source.parent.mkdir(parents=True)
    source.write_text(_skill_text(name, "# Canonical\n"), encoding="utf-8")
    if setup:
        setup_exit, _, setup_stderr = run_cli_with_homes(
            ["setup"],
            project,
            codex_home,
            codexmgr_home,
        )
        assert setup_exit == 0, setup_stderr
    enable_exit, _, enable_stderr = run_cli_with_homes(
        ["skill", "enable", name],
        project,
        codex_home,
        codexmgr_home,
    )
    assert enable_exit == 0, enable_stderr
    return source, project / ".agents" / "skills" / name / "SKILL.md"


def _skill_text(name: str, body: str) -> str:
    """Build valid skill text for a named test skill.

    Args:
        name: Skill name stored in YAML frontmatter.
        body: Markdown body following the frontmatter.

    Returns:
        Complete valid skill text.
    """
    return f"---\nname: {name}\ndescription: Test skill.\n---\n\n{body}"


class _InteractiveInput(io.StringIO):
    """String input stream that reports terminal interactivity."""

    def isatty(self) -> bool:
        """Report that the in-memory stream should receive prompts.

        Returns:
            Always ``True``.
        """
        return True
