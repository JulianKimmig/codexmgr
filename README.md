# codexmgr

`codexmgr` manages project-local Codex configuration from reusable templates.
It keeps hand-written project instructions in `AGENTS.md` and generated Codex
configuration in `.codex/` synchronized from a small declarative
`.codex/codexmgr.toml` file. It can also keep project-local MCP server
overrides in sync without editing the user Codex config.

The tool is intentionally narrow:

- compose reusable AGENTS.md instruction fragments
- enable or disable Codex skills per project
- enable, disable, inspect, and update safe project-local MCP overrides
- write reproducible lock data for the resolved project configuration
- run `codex` with project `.codex/config.toml` values translated into `-c`
  overrides

## Requirements

- Python 3.11 or newer
- `uv` for local development
- `codex` on `PATH` only when using `codexmgr codex ...`

## Installation

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

Create the project `.codex/` directory:

```bash
codexmgr setup
```

Create or install a named AGENTS.md template under
`$CODEXMGR_HOME/agentsmd/<name>.toml`. If `CODEXMGR_HOME` is unset,
`~/.codexmgr` is used.

```toml
[coding]
text = """
- Keep source files focused and small.
- Add tests for behavior changes before implementation.
"""

[coding.debugging]
text = "Prefer lasting regression tests over temporary scripts."
```

Add the template to the current project:

```bash
codexmgr agentsmd add coding
```

This updates `.codex/codexmgr.toml`, runs `apply`, writes
`.codex/codexmgr.lock`, and refreshes the managed block in `AGENTS.md`.

## Managed Files

`codexmgr` reads and writes these project files:

- `.codex/codexmgr.toml`: source configuration edited by CLI commands or by
  hand
- `.codex/codexmgr.lock`: resolved template, skill, and MCP state written by
  `apply`
- `.codex/config.toml`: Codex config updated with `[[skills.config]]` entries
  and `[mcp_servers.<id>]` overrides
- `AGENTS.md`: project instructions, with only the managed block replaced

The managed AGENTS.md block is:

```markdown
<!-- BEGIN CODEXMGR GENERATED -->
<!-- END CODEXMGR GENERATED -->
```

Manual content outside this block is preserved. If the block is missing,
`codexmgr` appends it. If `AGENTS.md` is missing, `codexmgr` creates it.

## Project Configuration

`.codex/codexmgr.toml` supports AGENTS.md templates, skill state, and MCP
overrides:

```toml
[agents_md]
src = ["coding", "/absolute/or/project-relative/template.toml"]

[skills]
enabled = ["review-helper"]
disabled = ["experimental-skill", "skills/local-disabled"]

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

Mutating commands run `apply` automatically unless `--no-sync` is passed.
Project guidelines require `apply` whenever `.codex/codexmgr.toml` changes,
unless `--no-sync` was explicitly requested.

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
codexmgr agentsmd list
codexmgr agentsmd show <name-or-template-path>
codexmgr agentsmd validate <name-or-template-path>
codexmgr agentsmd add [--no-sync] <name-or-template-path>
codexmgr agentsmd remove [--no-sync] <name-or-template-path>
codexmgr init-template agentsmd <name>
codexmgr skill list
codexmgr skill enable [--no-sync] <name-or-skill-path>
codexmgr skill disable [--no-sync] <name-or-skill-path>
codexmgr mcp list
codexmgr mcp show <server-id>
codexmgr mcp validate
codexmgr mcp enable [--no-sync] <server-id>
codexmgr mcp disable [--no-sync] <server-id>
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
`[skills]` table is configured, writes local `[mcp_servers.<id>]` overrides when
`[mcp]` is configured, and refreshes the generated `AGENTS.md` block when
`[agents_md]` is configured.

`apply --check` exits with a failure if generated files are out of sync without
writing them. `apply --diff` also avoids writing and prints unified diffs for
the expected generated-file changes.

`cd` launches a shell in `$CODEXMGR_HOME`. Use
`codexmgr cd --path` to print only the path, `codexmgr cd --explorer` to open
the directory in a file explorer, and `codexmgr cd --terminal` to open a new
terminal there.

`doctor` checks project setup, home environment variables, project TOML syntax,
referenced snippets, enabled skills, and stale generated files.

`status` prints the resolved homes, configured snippets and skills, and whether
generated files are in sync.

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
