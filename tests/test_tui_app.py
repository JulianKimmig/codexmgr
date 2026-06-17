"""Headless interaction tests for the Textual codexmgr TUI."""

import pytest

from codexmgr.tui.app import CodexMgrTui


@pytest.mark.asyncio
async def test_tui_app_toggles_skill_and_saves_without_sync(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The Skills screen lets users select a skill and save staged changes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("3")
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["skills"] == {
        "enabled": ["review"],
        "disabled": [],
    }
    assert not (project / ".agents" / "skills" / "review").exists()


@pytest.mark.asyncio
async def test_tui_app_toggles_agent_and_saves_without_sync(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The Agents screen lets users select a custom agent and save changes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "reviewer")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("5")
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["agents"] == {
        "enabled": ["reviewer"],
        "disabled": [],
    }
    assert not (project / ".codex" / "agents" / "reviewer.toml").exists()


@pytest.mark.asyncio
async def test_tui_app_cycles_skill_to_disabled_and_available(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The space action cycles skills through enabled, disabled, and available."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("3")
        await pilot.press("space")
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": ["review"],
    }

    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("3")
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": [],
    }


@pytest.mark.asyncio
async def test_tui_app_toggles_package_profile_and_saves_without_sync(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_project_config,
):
    """The Packages screen lets users select a package profile row."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "strict-coding", "[rules]\ntext = \"strict\"\n")
    _write_skill(codexmgr_home, "strict-review")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
[profiles.strict]
agentsmd = ["strict-coding"]
skills = ["strict-review"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("7")
        await pilot.press("down")
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project) == {
        "agents_md": {"src": ["strict-coding"]},
        "skills": {"enabled": ["strict-review"], "disabled": []},
    }


def _write_skill(home, name):
    """Create a codexmgr-home skill for tests.

    Args:
        home: Codexmgr home directory.
        name: Skill directory name.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file


def _write_agent(home, name):
    """Create a codexmgr-home custom agent for tests.

    Args:
        home: Codexmgr home directory.
        name: Agent file stem.

    Returns:
        Path to the created custom-agent TOML file.
    """
    agents_dir = home / "agents"
    agents_dir.mkdir(parents=True)
    path = agents_dir / f"{name}.toml"
    path.write_text('name = "agent"\n', encoding="utf-8")
    return path


def _write_package(home, name, content):
    """Create a codexmgr-home package for tests.

    Args:
        home: Codexmgr home directory.
        name: Package directory name.
        content: Package config TOML.

    Returns:
        Path to the created config.toml file.
    """
    package_dir = home / "packages" / name
    package_dir.mkdir(parents=True)
    path = package_dir / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path
