# codexmgr

`codexmgr` centralizes reusable Codex project setup. It lets you keep shared
`AGENTS.md` snippets, skills, hooks, custom agents, rule files, packages, and
safe MCP overrides in one manager home, then sync the selected pieces into each
project from a small `.codex/codexmgr.toml` file.

I built it because I use Codex in many different projects and got tired of
manually assembling `AGENTS.md` every time. When I improved a rule in one
project, I also had to remember to copy that update into every other project.
This workflow makes agent rules and snippets reusable, centralized, and still
project-specific where needed.

Use `codexmgr` when you want to:

- compose project `AGENTS.md` files from reusable instruction fragments
- keep shared rules, skills, hooks, and custom agents available across projects
- bundle common Codex setup as packages and profiles
- manage project-local MCP enablement without editing the user Codex config
- check whether generated Codex files are in sync
- run `codex` with project `.codex/config.toml` values translated into `-c`
  overrides

## Requirements

- Python 3.11 or newer
- `uv` for local development
- `codex` on `PATH` only when using `codexmgr codex ...`

## Install

From a checkout:

```bash
uv sync --group dev
uv run codexmgr --help
```

For local command-line use from this repository:

```bash
uv tool install .
```

## Quick Start

In a project that should use shared Codex configuration, initialize
`codexmgr`:

```bash
codexmgr setup
```

Create or install an `AGENTS.md` snippet under
`$CODEXMGR_HOME/agentsmd/<name>.toml`. If `CODEXMGR_HOME` is unset,
`codexmgr` uses `~/.codexmgr`.

```toml
[coding]
text = """
- Keep source files focused and small.
- Add tests for behavior changes before implementation.
"""

[coding.debugging]
text = "Prefer lasting regression tests over temporary scripts."
```

Add the snippet to the current project:

```bash
codexmgr agentsmd add coding
```

This updates `.codex/codexmgr.toml`, runs `apply`, writes
`.codex/codexmgr.lock`, and refreshes the managed block in `AGENTS.md`.

To preview or validate a snippet before adding it:

```bash
codexmgr agentsmd show coding
codexmgr agentsmd validate coding
```

## Managed Files

`codexmgr` reads and writes these project files:

- `.codex/codexmgr.toml`: source configuration edited by CLI commands or by
  hand
- `.codex/codexmgr.lock`: resolved template, agent, skill, hook, and MCP state
  written by `apply`
- `.codex/config.toml`: Codex config updated with `[[skills.config]]` entries
  and `[mcp_servers.<id>]` overrides
- `.codex/hooks.json`: Codex hook config updated with enabled reusable hook
  bundles while preserving unmanaged local hooks
- `.codex/hooks/<name>`: project-local copies of enabled hook bundle support
  files
- `.codex/agents/<name>.toml`: project-local copies of enabled custom agents
- `.rules/<path>`: project-local copies of enabled reusable rule files
- `AGENTS.md`: project instructions, with only the managed block replaced

The managed AGENTS.md block is:

```markdown
<!-- BEGIN CODEXMGR GENERATED -->
<!-- END CODEXMGR GENERATED -->
```

Manual content outside this block is preserved. If the block is missing,
`codexmgr` appends it. If `AGENTS.md` is missing, `codexmgr` creates it.

## Project Configuration

`.codex/codexmgr.toml` supports AGENTS.md templates, custom-agent state, skill
state, hook state, and MCP overrides:

```toml
[agents_md]
src = ["coding", "/absolute/or/project-relative/template.toml"]

[skills]
enabled = ["review-helper"]
disabled = ["experimental-skill", "skills/local-disabled"]

[agents]
enabled = ["rule-retriever"]
disabled = ["experimental-agent"]

[hooks]
enabled = ["repo-rules"]
disabled = ["experimental-hook"]

[rules]
enabled = ["react/", "python/testing.md"]
disabled = ["react/materials/"]

[mcp.servers.browsermcp]
enabled = true
bearer_token_env_var = "BROWSERMCP_TOKEN"
env_vars = ["BROWSER_ENV"]
```

Named AGENTS.md templates resolve from `$CODEXMGR_HOME/agentsmd/<name>.toml`.
Path-like template values resolve relative to the project unless they are
absolute paths.

Named skills resolve from `$CODEXMGR_HOME/skills/<name>/SKILL.md` or
`$CODEX_HOME/skills/<name>/SKILL.md`; duplicate names across distinct homes
fail. Enabled CODEXMGR_HOME skills are copied into `.agents/skills/<name>` on
every apply by overlaying source files while preserving extra local files.
Path-like skill values resolve to either a `SKILL.md` file or a directory
containing `SKILL.md`. Missing skills are written as name-based entries so Codex
can resolve them later.

Named custom agents resolve from `$CODEXMGR_HOME/agents/<name>.toml`. Enabled
agents are copied into `.codex/agents/<name>.toml` on every apply. Disabled
agents remove their managed copy only when the lock records the file as
codexmgr-managed.

Named hooks resolve from `$CODEXMGR_HOME/hooks/<name>/hooks.json`. Enabled hook
bundles are merged into `.codex/hooks.json` on every apply with
`codexmanager_meta` added to each managed handler. Existing unmanaged hooks are
preserved. Bundle files other than the root `hooks.json` are copied into
`.codex/hooks/<name>`.

Rule refs resolve under `$CODEXMGR_HOME/rules/` and are POSIX-style relative
paths. Folder refs are stored with a trailing slash and copy all regular files
recursively into `.rules/` while preserving relative paths. File refs copy one
file. Extensionless refs prefer an existing `<ref>.md`. Enabled refs expand
first, then disabled file or folder refs remove entries from that candidate set.
First-time applies refuse to overwrite unmanaged `.rules/...` files.

Packaged configurations resolve from
`$CODEXMGR_HOME/packages/<name>/config.toml`. A package config is a TOML
document that can contain root `agentsmd`, `agents`, `hooks`, `skills`, and `rules`
string lists plus optional profile tables:

```toml
agentsmd = []
agents = ["rule-retriever"]
hooks = ["repo-rules"]
skills = ["repo-rule-manager"]
rules = ["react/"]

[profiles.strict]
agentsmd = ["strict-coding"]
agents = ["strict-agent"]
hooks = ["strict-rules"]
skills = ["strict-review"]
rules = ["python/testing.md"]
```

`codexmgr package enable <name>` validates package AGENTS.md and hook
references, then updates `.codex/codexmgr.toml` as if the corresponding
`agentsmd add`, `hooks enable`, and `skill enable` commands had been run.
`codexmgr package disable <name>` removes package AGENTS.md entries when
present and disables the package skills, hooks, agents, and rules.

Package profiles are merged with the root package entries:

```bash
codexmgr package enable repo-rules --profile strict coding --profile python
```

Direct mutating commands also accept batch targets, for example:

```bash
codexmgr agentsmd add coding python
codexmgr skill enable review-helper repo-rule-manager
codexmgr hooks enable repo-rules audit
codexmgr mcp enable browsermcp context7
```

Mutating commands run `apply` automatically unless `--no-sync` is passed.
Project guidelines require `apply` whenever `.codex/codexmgr.toml` changes,
unless `--no-sync` was explicitly requested.

## Interactive TUI

`codexmgr tui` opens a Textual-based terminal UI for managing project-local
configuration. It shows AGENTS.md templates, skills, hooks, custom agents,
rules, packages, and MCP server enable overrides in selectable lists. Changes are
staged in memory while you navigate and toggle entries. Press `s` to save; the
save writes `.codex/codexmgr.toml` once and runs `apply` once unless
`--no-sync` was used.
For resources with explicit enable and disable lists, `space` cycles the
highlighted row through available, enabled, and disabled states.
Package profiles appear as separate selectable rows under their package.

```bash
codexmgr tui
codexmgr tui --no-sync
codexmgr tui --show-diff
```

The dashboard shows generated-file sync state. By default it lists stale
generated paths; with `--show-diff`, it shows unified diffs for the staged
configuration. MCP editing in the TUI is intentionally limited to the
project-local `enabled` override. Advanced MCP fields remain available through
the classic `codexmgr mcp ...` commands.

## Template Format

Template files are TOML documents. Each top-level key must be a table and
becomes an AGENTS.md heading. A `text` value inside a table becomes the body
under that heading. Nested tables become nested headings.

```toml
[coding]
text = "Top-level guidance."

[coding.tests]
text = "Test behavior, not implementation details."
```

renders as:

```markdown
# coding
Top-level guidance.

## tests
Test behavior, not implementation details.
```

Unsupported scalar entries fail loudly instead of being silently ignored. This
keeps template mistakes visible during `apply`.

## Commands

```bash
codexmgr setup
codexmgr apply
codexmgr apply --check
codexmgr apply --diff
codexmgr cd [--path | --explorer | --terminal]
codexmgr doctor
codexmgr status
codexmgr tui [--no-sync] [--show-diff]
codexmgr agentsmd list
codexmgr agentsmd show <name-or-template-path>
codexmgr agentsmd validate <name-or-template-path>
codexmgr agentsmd add [--no-sync] <name-or-template-path> [...]
codexmgr agentsmd remove [--no-sync] <name-or-template-path> [...]
codexmgr init-template agentsmd <name>
codexmgr skill list
codexmgr skill enable [--no-sync] <name-or-skill-path> [...]
codexmgr skill disable [--no-sync] <name-or-skill-path> [...]
codexmgr agents list
codexmgr agents enable [--no-sync] <agent-name> [...]
codexmgr agents disable [--no-sync] <agent-name> [...]
codexmgr hooks list
codexmgr hooks enable [--no-sync] <hook-name> [...]
codexmgr hooks disable [--no-sync] <hook-name> [...]
codexmgr rules list
codexmgr rules enable [--no-sync] <rule-ref> [...]
codexmgr rules disable [--no-sync] <rule-ref> [...]
codexmgr package list
codexmgr package enable [--no-sync] <package-name> [...] [--profile <name> [...]]
codexmgr package disable [--no-sync] <package-name> [...] [--profile <name> [...]]
codexmgr mcp list
codexmgr mcp show <server-id>
codexmgr mcp validate
codexmgr mcp enable [--no-sync] <server-id> [...]
codexmgr mcp disable [--no-sync] <server-id> [...]
codexmgr mcp set-token-env [--no-sync] <server-id> <ENV_VAR>
codexmgr mcp add-env-var [--no-sync] <server-id> <ENV_VAR>
codexmgr mcp remove-env-var [--no-sync] <server-id> <ENV_VAR>
codexmgr mcp set-env-header [--no-sync] <server-id> <HEADER> <ENV_VAR>
codexmgr mcp unset-env-header [--no-sync] <server-id> <HEADER>
codexmgr mcp set-field [--no-sync] <server-id> <field> <toml-value>
codexmgr codex <args...>
```

`setup` creates `.codex/` in the current project.

`apply` reads `.codex/codexmgr.toml`, resolves configured sources, writes
`.codex/codexmgr.lock`, updates `.codex/config.toml` skill entries when a
`[skills]` table is configured, copies `.codex/agents/<name>.toml` files when
`[agents]` is configured, writes `.codex/hooks.json` when `[hooks]` is
configured, copies `.rules/<path>` files when `[rules]` is configured, writes
local `[mcp_servers.<id>]` overrides when `[mcp]` is
configured, and refreshes the generated `AGENTS.md` block when `[agents_md]` is
configured.

`apply --check` exits with a failure if generated files are out of sync without
writing them. `apply --diff` also avoids writing and prints unified diffs for
the expected generated-file changes.

`cd` launches a shell in `$CODEXMGR_HOME`. Use
`codexmgr cd --path` to print only the path, `codexmgr cd --explorer` to open
the directory in a file explorer, and `codexmgr cd --terminal` to open a new
terminal there.

`doctor` checks project setup, home environment variables, project TOML syntax,
referenced snippets, enabled skills, enabled custom agents, enabled hook
bundles, enabled rules, and stale generated files.

`status` prints the resolved homes, configured snippets, skills, custom agents,
hooks, rules, and whether generated files are in sync.

`codexmgr codex` can run with a just-in-time package/profile overlay without
changing `.codex/codexmgr.toml`. Put Codex arguments after `--` when using this
syntax:

```bash
codexmgr codex repo-rules --profile strict coding --profile python -- exec "review this"
```

## Project MCP Overrides

`codexmgr mcp ...` edits only project-local configuration:

- source state is stored in `.codex/codexmgr.toml` under
  `[mcp.servers.<id>]`
- `apply` writes generated overrides into `.codex/config.toml` under
  `[mcp_servers.<id>]`
- `$CODEX_HOME/config.toml` and `~/.codex/config.toml` are never modified

Mutating MCP commands require a project `.codex/` directory and run `apply`
automatically unless `--no-sync` is passed. They do not create or remove MCP
server definitions; use `codex mcp add` or direct Codex config editing for the
base server setup.

List MCP servers available from Codex and show any project override state:

```bash
codexmgr mcp list
codexmgr mcp show context7
codexmgr mcp validate
```

`codexmgr mcp list` shells out to `codex mcp list --json` for read-only
discovery. It does not edit user configuration.

Enable or disable an existing server without deleting its definition:

```bash
codexmgr mcp disable context7
codexmgr mcp enable context7
```

Update token and environment references without storing literal token values:

```bash
codexmgr mcp set-token-env figma FIGMA_TOKEN
codexmgr mcp add-env-var context7 CONTEXT7_TOKEN
codexmgr mcp remove-env-var context7 CONTEXT7_TOKEN
codexmgr mcp set-env-header figma Authorization FIGMA_AUTH_HEADER
codexmgr mcp unset-env-header figma Authorization
```

Set a small allowlist of non-secret fields from TOML literals:

```bash
codexmgr mcp set-field context7 required true
codexmgr mcp set-field context7 enabled_tools '["search", "open"]'
codexmgr mcp set-field context7 default_tools_approval_mode '"prompt"'
```

Supported `set-field` names are `required`, `startup_timeout_sec`,
`tool_timeout_sec`, `enabled_tools`, `disabled_tools`, and
`default_tools_approval_mode`. The direct `enable` and `disable` commands manage
the `enabled` field.

Literal API token writes are intentionally not part of this command surface;
prefer environment variable references such as `bearer_token_env_var`,
`env_vars`, and `env_http_headers`.

`agentsmd list` prints the named templates available under
`$CODEXMGR_HOME/agentsmd` in sorted order.

`agentsmd show` renders one template as AGENTS.md markdown without changing the
project configuration. `agentsmd validate` loads and renders a template to catch
TOML or template-shape errors before adding it.

`agentsmd add` validates that the template exists before writing config.
Repeated adds keep one source entry.

`agentsmd remove` removes a configured template source and fails if the source
is not present.

`init-template agentsmd` creates a starter template under
`$CODEXMGR_HOME/agentsmd` and refuses to overwrite an existing template.

`skill list` prints available `$CODEXMGR_HOME/skills/*/SKILL.md`,
`$CODEX_HOME/skills/*/SKILL.md`, and local `.agents/skills/*/SKILL.md` entries
and marks configured skills as enabled, disabled, or missing.

`skill enable` and `skill disable` keep enabled and disabled lists mutually
exclusive. Repeated commands keep one entry.

`hooks list` prints available `$CODEXMGR_HOME/hooks/*/hooks.json` entries and
marks configured hook bundles as enabled, disabled, or missing.

`hooks enable` validates that the named hook bundle exists before writing
config. `hooks enable` and `hooks disable` keep enabled and disabled lists
mutually exclusive. Repeated commands keep one entry.

`rules list` prints available `$CODEXMGR_HOME/rules/**` files and folders and
marks configured rule refs as enabled, disabled, or missing.

`rules enable` validates and canonicalizes refs before writing config.
`rules disable` canonicalizes existing refs and permits missing exclusions.
Enabled and disabled lists are exact-ref mutually exclusive, so parent enables
and child disables can intentionally coexist.

`package list` prints available `$CODEXMGR_HOME/packages/*/config.toml`
entries in sorted order.

`package enable` and `package disable` proxy to existing AGENTS.md, custom-agent,
skill, hook, and rule project-config mutations. Package state is not tracked
separately; the resulting `[agents_md]`, `[agents]`, `[skills]`, `[hooks]`, and `[rules]`
tables remain the source of truth.

`codex` forwards arguments to the real `codex` command. Values from
`.codex/config.toml` are flattened into `-c key=value` overrides. User-provided
`-c` or `--config` overrides are merged after project config: scalar values
replace earlier values, while list values append.

## Development

Install dependencies:

```bash
uv sync --group dev
```

Run tests:

```bash
uv run pytest
```

Build distributions:

```bash
uv build
```

The package is typed (`py.typed`) and the test suite covers CLI behavior,
template rendering, TOML writing, skill resolution, generated-file sync checks,
Codex command generation, home-directory resolution, and package metadata.

## Release Notes

The GitHub workflow runs the test matrix on Python 3.11, 3.12, and 3.13 across
Linux, Windows, and macOS. The publish workflow builds and publishes to PyPI
when the version in `pyproject.toml` differs from the latest published version.
