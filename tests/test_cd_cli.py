"""CLI tests for codexmgr home navigation helpers."""

import shlex


def test_cd_outputs_shell_cd_command(workspace, run_cli_with_homes):
    """cd prints shell code that changes into CODEXMGR_HOME when evaluated."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == f"cd {shlex.quote(str(codexmgr_home))}\n"


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
    run_cli_with_homes,
):
    """cd --explorer prints shell code that opens CODEXMGR_HOME in a file explorer."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd", "--explorer"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == f"xdg-open {shlex.quote(str(codexmgr_home))}\n"


def test_cd_terminal_option_outputs_new_terminal_command(
    workspace,
    run_cli_with_homes,
):
    """cd --terminal prints shell code that opens a terminal in CODEXMGR_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr home"

    exit_code, stdout, stderr = run_cli_with_homes(
        ["cd", "--terminal"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    quoted_home = shlex.quote(str(codexmgr_home))
    assert stdout == f"x-terminal-emulator --working-directory {quoted_home}\n"
