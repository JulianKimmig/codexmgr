"""CLI tests for codexmgr home navigation helpers."""

from types import SimpleNamespace

from codexmgr import navigation


def test_cd_launches_shell_in_codexmgr_home(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """cd launches the configured shell inside CODEXMGR_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"
    codexmgr_home.mkdir()
    calls = []

    def fake_run(command, cwd):
        """Record an external command instead of running it."""
        calls.append((command, cwd))
        return SimpleNamespace(returncode=23)

    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.setattr(navigation.subprocess, "run", fake_run)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 23
    assert stderr == ""
    assert stdout == ""
    assert calls == [(["/bin/zsh"], codexmgr_home)]


def test_cd_fails_when_shell_is_not_configured(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """cd fails loudly when no current-terminal shell can be detected."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    codexmgr_home.mkdir()

    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.delenv("COMSPEC", raising=False)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Shell not configured" in stderr


def test_cd_path_option_outputs_raw_codexmgr_home_path(workspace, run_cli_with_homes):
    """cd --path prints CODEXMGR_HOME without shell command wrapping."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd", "--path"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == f"{codexmgr_home}\n"


def test_cd_explorer_option_outputs_file_explorer_command(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """cd --explorer opens CODEXMGR_HOME in a file explorer."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"
    codexmgr_home.mkdir()
    calls = []

    def fake_run(command, cwd):
        """Record an external command instead of running it."""
        calls.append((command, cwd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(navigation.sys, "platform", "linux")
    monkeypatch.setattr(navigation.subprocess, "run", fake_run)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd", "--explorer"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == ""
    assert calls == [(["xdg-open", str(codexmgr_home)], None)]


def test_cd_terminal_option_outputs_new_terminal_command(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """cd --terminal opens a new terminal in CODEXMGR_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"
    codexmgr_home.mkdir()
    calls = []

    def fake_run(command, cwd):
        """Record an external command instead of running it."""
        calls.append((command, cwd))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(navigation.sys, "platform", "linux")
    monkeypatch.setattr(navigation.subprocess, "run", fake_run)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd", "--terminal"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == ""
    assert calls == [
        (["x-terminal-emulator", "--working-directory", str(codexmgr_home)], None)
    ]
