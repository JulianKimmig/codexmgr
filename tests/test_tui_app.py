"""Headless interaction tests for the Textual codexmgr TUI."""

import pytest
from textual.widgets import Tree

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


@pytest.mark.asyncio
async def test_tui_app_cycles_rule_folder_tree_node(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The Rules screen cycles a folder tree node using its canonical ref."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("6")
        await pilot.pause()
        tree = app.query_one("#rule-tree", Tree)
        tree.select_node(tree.root.children[0])
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["rules"] == {
        "enabled": ["react/"],
        "disabled": [],
    }


@pytest.mark.asyncio
async def test_tui_app_cycles_nested_rule_file_tree_node(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The Rules screen cycles nested file nodes using full canonical refs."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md")
    _write_rule(codexmgr_home, "react/materials/colors.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("6")
        await pilot.pause()
        tree = app.query_one("#rule-tree", Tree)
        react_node = tree.root.children[0]
        colors_node = react_node.children[1].children[0]
        react_node.expand()
        react_node.children[1].expand()
        await pilot.pause()
        tree.move_cursor_to_line(colors_node.line)
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["rules"] == {
        "enabled": ["react/materials/colors.md"],
        "disabled": [],
    }


@pytest.mark.asyncio
async def test_tui_app_renders_nested_missing_rule_tree_node(
    workspace,
    run_cli_with_homes,
):
    """The Rules screen renders missing nested refs under virtual folders."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '[rules]\ndisabled = ["legacy/deep.md"]\n',
        encoding="utf-8",
    )
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("6")
        await pilot.pause()
        tree = app.query_one("#rule-tree", Tree)
        legacy_node = tree.root.children[0]
        missing_item = legacy_node.children[0].data

    assert legacy_node.data is None
    assert missing_item.name == "legacy/deep.md"
    assert missing_item.state == "disabled"
    assert missing_item.missing is True


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
    skill_file.write_text(
        f"---\nname: {name}\ndescription: Test skill.\n---\n\n# Skill\n",
        encoding="utf-8",
    )
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


def _write_rule(home, relative_path):
    """Create a codexmgr-home reusable rule for tests.

    Args:
        home: Codexmgr home directory.
        relative_path: POSIX path below the reusable rules root.

    Returns:
        Path to the created rule file.
    """
    path = home / "rules" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Rule\n", encoding="utf-8")
    return path
