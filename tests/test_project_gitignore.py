"""Behavioral tests for the managed project Codex ignore file."""

import subprocess


BEGIN = "# BEGIN CODEXMGR GENERATED"
END = "# END CODEXMGR GENERATED"
MANAGED_BODY = """*
!/.gitignore
!/codexmgr.toml
!/codexmgr.lock
!/config.toml
!/hooks.json
!/agents/
!/agents/**
!/hooks/
!/hooks/**
__pycache__/"""
MANAGED_BLOCK = f"{BEGIN}\n{MANAGED_BODY}\n{END}"


def test_setup_creates_future_proof_project_codex_gitignore(workspace, run_cli):
    """Setup default-ignores unknown state while allowing codexmgr files."""
    project, codex_home = workspace

    exit_code, _, stderr = run_cli(["setup"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert (project / ".codex" / ".gitignore").read_text(encoding="utf-8") == (
        f"{MANAGED_BLOCK}\n"
    )


def test_setup_preserves_manual_project_codex_gitignore_content(workspace, run_cli):
    """Setup appends its managed block without deleting manual ignore rules."""
    project, codex_home = workspace
    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "codexmgr.toml").write_text("", encoding="utf-8")
    (codex_dir / ".gitignore").write_text("manual-cache/\n", encoding="utf-8")

    exit_code, _, stderr = run_cli(["setup"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert (codex_dir / ".gitignore").read_text(encoding="utf-8") == (
        f"manual-cache/\n\n{MANAGED_BLOCK}\n"
    )


def test_apply_repairs_managed_gitignore_block_and_preserves_manual_content(
    workspace,
    run_cli,
):
    """Apply replaces only a stale codexmgr block inside the ignore file."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    gitignore = project / ".codex" / ".gitignore"
    gitignore.write_text(
        f"manual-before/\n\n{BEGIN}\nold-runtime-file\n{END}\n\nmanual-after/\n",
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert gitignore.read_text(encoding="utf-8") == (
        f"manual-before/\n\n{MANAGED_BLOCK}\n\nmanual-after/\n"
    )


def test_managed_gitignore_ignores_unknown_runtime_state_only(workspace, run_cli):
    """Git ignores future runtime names but exposes every codexmgr-owned path."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    runtime_file = project / ".codex" / "future-runtime-state.bin"
    runtime_file.write_text("runtime\n", encoding="utf-8")
    agent_file = project / ".codex" / "agents" / "local.toml"
    agent_file.parent.mkdir()
    agent_file.write_text("name = \"local\"\n", encoding="utf-8")
    hook_file = project / ".codex" / "hooks" / "local" / "handler.py"
    hook_file.parent.mkdir(parents=True)
    hook_file.write_text("print('hook')\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )

    assert _git_check_ignore(project, ".codex/future-runtime-state.bin") == 0
    for managed_path in [
        ".codex/.gitignore",
        ".codex/codexmgr.toml",
        ".codex/config.toml",
        ".codex/agents/local.toml",
        ".codex/hooks/local/handler.py",
    ]:
        assert _git_check_ignore(project, managed_path) == 1


def test_apply_check_reports_missing_project_codex_gitignore(workspace, run_cli):
    """Apply check treats a missing managed ignore block as stale state."""
    project, codex_home = workspace
    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "codexmgr.toml").write_text("", encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["apply", "--check"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "Out of sync: .codex/.gitignore" in stdout
    assert not (codex_dir / ".gitignore").exists()


def test_apply_rejects_incomplete_managed_gitignore_block(workspace, run_cli):
    """Apply fails visibly instead of overwriting a malformed managed block."""
    project, codex_home = workspace
    codex_dir = project / ".codex"
    codex_dir.mkdir()
    (codex_dir / "codexmgr.toml").write_text("", encoding="utf-8")
    gitignore = codex_dir / ".gitignore"
    original = f"manual-cache/\n\n{BEGIN}\nstale\n"
    gitignore.write_text(original, encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert stderr == "Incomplete CODEXMGR generated block in .codex/.gitignore\n"
    assert gitignore.read_text(encoding="utf-8") == original


def _git_check_ignore(project, relative_path):
    """Return Git's ignore-match exit code for one project-relative path.

    Args:
        project: Temporary Git repository root.
        relative_path: Path whose ignore state should be queried.

    Returns:
        Zero when ignored and one when visible to Git.
    """
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", relative_path],
        cwd=project,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode
