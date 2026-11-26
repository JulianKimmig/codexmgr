# Changelog

This file records changes to the codexmgr Python package and CLI. codexmgr uses `MAJOR.MINOR.PATCH` versions. During the 0.x series, check entries marked **Breaking** before upgrading. Release dates use UTC and reflect [PyPI publication](https://pypi.org/project/codexmgr/#history).

## Unreleased

### Fixed

- `codexmgr codex` continues with project-local authentication if the OS cannot create the global auth symlink, including on Windows mapped network drives. Sign in for the project if Codex prompts you.

## 0.5.3 - 2026-11-26

### Fixed

- `codexmgr codex` can find global authentication in the default user home when `HOME` is unset or empty. If Windows denies permission to create the authentication symlink, the launcher preserves any existing project auth and continues. If prompted, sign in for the project.

## 0.5.2 - 2026-09-28

### Added

- Discover nested skills using references such as `team/review`. Select a whole skill group with a trailing slash in the CLI, in a package, or in the TUI. Group selection enables the skills present at the time of selection.
- Enable reusable guide files and folders with `codexmgr guides enable`, a package, or the TUI. Guides and their supporting files are copied under `.guides/` with their relative paths intact.
- When you add a file inside an enabled rule or guide folder, `apply` and TUI save offer to add it to the shared store or keep it project-only. In scripts, use `apply --resolve <target-path> update-source` or `apply --resolve <target-path> keep-local` to record that choice.

## 0.5.1 - 2026-08-31

### Changed

- Apply and TUI save now ask how to handle differing files in managed copies of skills, rules, agents, and hook support files. Noninteractive applies with conflicts require `--resolve <target-path> <action>` for each target.

### Fixed

- Managed agent, hook, and rule copy locks resolve against the current project and manager home after moving or cloning a project. Apply migrates legacy absolute entries so cleanup stays within the current project.

## 0.5.0 - 2026-07-23

### Changed

- **Breaking:** Missing explicit skill paths now cause apply to fail. Correct missing paths, qualify ambiguous folder names with an explicit path, and give discoverable skills unique frontmatter names.
- Project-local and managed skills now generate portable selectors based on their `SKILL.md` frontmatter name. Apply migrates existing skill copy locks to project-relative targets.

## 0.4.1 - 2026-07-23

### Fixed

- `codexmgr codex` now uses `.codex/.runtime` for mutable Codex state and the authentication link. Trust the project in Codex to load the tracked `.codex/config.toml`.

## 0.4.0 - 2026-07-22

### Changed

- **Breaking:** `codexmgr codex` now sets the project's `.codex` directory as `CODEX_HOME` and passes your arguments through unchanged. Use `codexmgr codex --simple` for launches that use the existing Codex home and skip project apply.
- Apply now maintains a `.codex/.gitignore` block that hides runtime files by default and exposes managed project configuration. Custom rules outside the block are preserved.

## 0.3.0 - 2026-07-07

### Added

- Reuse MCP server definitions across projects by storing them in `$CODEXMGR_HOME/mcp/*.toml`. Project settings under `[mcp.servers.<id>]` can override those definitions.

### Changed

- **Breaking:** `codexmgr mcp enable` and `disable` now load and unload reusable sources by name. If your scripts toggled an existing server by ID, move that setting to `[mcp.servers.<id>].enabled` in project configuration.
- `codexmgr rules list` and the TUI Rules screen now group rule sources by folder.

### Fixed

- The TUI retains focus on the selected entry when cycling its state, including entries in nested rule folders.

## 0.2.1 - 2026-06-17

This release refreshed installation and onboarding documentation and expanded test coverage for custom agents in packages.

## 0.2.0 - 2026-06-17

### Added

- Enable reusable Codex custom agents with `codexmgr agents enable`. Their definitions are copied to the project's `.codex/agents/` directory.
- Enable shared rule files or whole rule folders with `codexmgr rules enable`. Rules are copied to `.rules/`, and packages can bundle them alongside custom agents and other inputs.

## 0.1.3 - 2026-06-17

### Added

- Enable bundles of AGENTS.md snippets, skills, and hooks with `codexmgr package enable`. Use profiles to add optional inputs, including for a single `codexmgr codex` invocation.
- Manage project selections interactively with `codexmgr tui` and save them together.
- Copy enabled manager-home skills into `.agents/skills/` and enable reusable hook bundles with `codexmgr hooks enable`. Apply merges managed hooks with existing project hooks.
- Pass multiple targets to selection commands such as `codexmgr skill enable` and `codexmgr hooks enable`.

### Changed

- `codexmgr setup` applies the project config immediately. `codexmgr codex` refreshes project configuration before launch.

## 0.1.2 - 2026-06-05

### Added

- Inspect existing Codex MCP servers and configure project-local overrides for enablement, token environment variables, headers, and server fields with `codexmgr mcp`.
- Use `codexmgr status` and `codexmgr doctor` to inspect configuration and diagnose sync problems. Use `codexmgr agentsmd list` to browse templates and `codexmgr cd` to open the manager home.

## 0.1.1 - 2026-06-05

### Fixed

- Restored Python 3.11 compatibility when importing the module that renders `AGENTS.md`.

## 0.1.0 - 2026-06-05

### Added

- Set up a Codex project with `codexmgr setup` and generate project configuration from `.codex/codexmgr.toml`. Compose reusable AGENTS.md snippets, select skills per project, and record resolved state in a lockfile.
- Launch Codex with project settings through `codexmgr codex`. The wrapper applies project configuration as `-c` overrides.
