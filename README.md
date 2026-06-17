# codexmgr

`codexmgr` manages reusable Codex project setup. Keep shared `AGENTS.md`
snippets, skills, hooks, custom agents, rule files, packages, and safe MCP
overrides in one manager home, then sync the selected pieces into each project
from `.codex/codexmgr.toml`.

The tool is for people who use Codex in several repositories and do not want to
copy the same agent instructions by hand. When a shared rule changes, update it
once in `$CODEXMGR_HOME` and apply it wherever that project has opted in.

Use `codexmgr` when a project should:

- build `AGENTS.md` from reusable instruction snippets
- share skills, hooks, custom agents, and rule files across repositories
- enable packaged Codex setups made from those reusable pieces
- keep project MCP overrides out of the user-level Codex config
- check whether generated Codex files match the project config
- run `codex` with project `.codex/config.toml` values passed as `-c` overrides

The basic model has three parts:

- `$CODEXMGR_HOME` stores reusable inputs; when unset it defaults to
  `~/.codexmgr`
- `.codex/codexmgr.toml` records what the current project wants to use
- `codexmgr apply` resolves the selected inputs and writes the project files
  Codex reads

## Requirements

- Python 3.11 or newer
- `codex` on `PATH` only when using `codexmgr codex ...`

## Install

Install `codexmgr` as a command-line tool from the Python package. `pipx` is
the recommended persistent install because it keeps the tool isolated from
project environments:

```bash
pipx install codexmgr
```

If you use `uv` for command-line tools:

```bash
uv tool install codexmgr
```

Plain `pip` also works inside an environment you control:

```bash
python -m pip install codexmgr
```

Verify the install:

```bash
codexmgr --help
```

## Quick Start

Start inside the project that should receive Codex configuration.

```bash
codexmgr setup
```

`setup` creates `.codex/`, creates `.codex/codexmgr.toml` if it is missing, and
runs `apply`. Existing project config is preserved.

Create a reusable `AGENTS.md` snippet in the manager home. This command creates
`$CODEXMGR_HOME/agentsmd/coding.toml` and refuses to overwrite an existing file:

```bash
codexmgr init-template agentsmd coding
```

You can also write the snippet yourself. A snippet is a TOML template whose
tables become Markdown headings in `AGENTS.md`:

```toml
# ~/.codexmgr/agentsmd/coding.toml
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

Preview or validate a snippet when you want to check it before adding it:

```bash
codexmgr agentsmd show coding
codexmgr agentsmd validate coding
```

Check what the project is using after changes:

```bash
codexmgr status
codexmgr doctor
codexmgr apply --check
```

## Managed Files

The project source of truth is `.codex/codexmgr.toml`. CLI commands edit this
file for you, and you can also edit it by hand when that is clearer.

`apply` resolves the source config and may write or update these managed files:

- `.codex/codexmgr.lock`: resolved AGENTS.md, agent, skill, hook, rule, and MCP
  state
- `.codex/config.toml`: project-local Codex config, including generated
  `[[skills.config]]` entries and `[mcp_servers.<id>]` overrides
- `.codex/hooks.json`: generated hook config for enabled reusable hook bundles
- `.codex/hooks/<name>`: copied support files for enabled hook bundles
- `.codex/agents/<name>.toml`: copied custom-agent definitions
- `.agents/skills/<name>`: copied manager-home skills
- `.rules/<path>`: copied reusable rule files
- `AGENTS.md`: project instructions with only the generated block replaced

The managed `AGENTS.md` block is:

```markdown
<!-- BEGIN CODEXMGR GENERATED -->
<!-- END CODEXMGR GENERATED -->
```

Manual content outside this block is preserved. If the block is missing,
`codexmgr` appends it. If `AGENTS.md` is missing, `codexmgr` creates it.

## Project Configuration

`.codex/codexmgr.toml` can opt into each resource type independently. A minimal
file may only contain `[agents_md]`; larger projects can add skills, custom
agents, hooks, reusable rules, and MCP overrides as needed. Package commands
write those same tables rather than a separate package table.

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

Mutating commands run `apply` automatically unless `--no-sync` is passed. If
you edit `.codex/codexmgr.toml` by hand, run `codexmgr apply` or
`codexmgr apply --check` afterwards.

## Reference Resolution

Named `AGENTS.md` snippets resolve from
`$CODEXMGR_HOME/agentsmd/<name>.toml`. Path-like snippet values resolve
relative to the project unless they are absolute paths.

Named skills resolve from `$CODEXMGR_HOME/skills/<name>/SKILL.md` or
`$CODEX_HOME/skills/<name>/SKILL.md`. Duplicate names across distinct homes
fail so the selected skill is not ambiguous.

Enabled skills from `$CODEXMGR_HOME` are copied into `.agents/skills/<name>` on
every apply. The copy overlays source files while preserving extra local files.
Path-like skill values can point to a `SKILL.md` file or a directory containing
`SKILL.md`.

Missing skills are still written as name-based entries. That lets Codex resolve
them later from another installed skill source.

Named custom agents resolve from `$CODEXMGR_HOME/agents/<name>.toml`. Enabled
agents are copied into `.codex/agents/<name>.toml`; disabled agents remove the
managed copy only when the lock records it as codexmgr-managed.

Named hooks resolve from `$CODEXMGR_HOME/hooks/<name>/hooks.json`. Enabled hook
bundles are merged into `.codex/hooks.json`, and existing unmanaged hooks are
preserved.

Hook bundle files other than the root `hooks.json` are copied into
`.codex/hooks/<name>`. Managed hook handlers receive `codexmanager_meta` so
future applies can distinguish them from local hooks.

Rule refs resolve under `$CODEXMGR_HOME/rules/` and use POSIX-style relative
paths. Folder refs have a trailing slash and copy regular files recursively into
`.rules/` while preserving relative paths.

File rule refs copy one file. Extensionless refs prefer an existing `<ref>.md`.
Enabled refs expand first, then disabled file or folder refs remove entries from
that candidate set.

First-time rule applies refuse to overwrite unmanaged `.rules/...` files. This
keeps existing project-local rules from being replaced accidentally.

## Packages

Packages are reusable bundles of snippets, agents, hooks, skills, and rules.
They resolve from `$CODEXMGR_HOME/packages/<name>/config.toml`.

A package config is a TOML document with root lists and optional profile tables:

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

The `agents` list enables custom agents from
`$CODEXMGR_HOME/agents/<name>.toml`.

`codexmgr package enable <name>` validates enabled package sources, then updates
`.codex/codexmgr.toml` as if the corresponding resource commands had been run.

`codexmgr package disable <name>` removes package `AGENTS.md` entries when
present and disables the package skills, hooks, agents, and rules. Package state
is not tracked separately; the resulting project config tables remain the
source of truth.

Profiles are merged with the root package entries:

```bash
codexmgr package enable repo-rules --profile strict python
```

Direct mutating commands also accept batch targets, for example:

```bash
codexmgr agentsmd add coding python
codexmgr skill enable review-helper repo-rule-manager
codexmgr hooks enable repo-rules audit
codexmgr mcp enable browsermcp context7
```

These commands run `apply` automatically unless `--no-sync` is passed.

## Interactive TUI

`codexmgr tui` opens a Textual-based terminal UI for project-local
configuration. It shows `AGENTS.md` snippets, skills, hooks, custom agents,
rules, packages, and MCP server enable overrides in selectable lists.

Changes are staged in memory while you navigate. Press `s` to save; the save
writes `.codex/codexmgr.toml` once and runs `apply` once unless `--no-sync` was
used.

For resources with explicit enable and disable lists, `space` cycles the
highlighted row through available, enabled, and disabled states. Package
profiles appear as separate selectable rows under their package.

```bash
codexmgr tui
codexmgr tui --no-sync
codexmgr tui --show-diff
```

The dashboard shows generated-file sync state. By default it lists stale
generated paths; with `--show-diff`, it shows unified diffs for the staged
configuration.

MCP editing in the TUI is intentionally limited to the project-local `enabled`
override. Advanced MCP fields remain available through the `codexmgr mcp ...`
commands.

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

This example renders a top-level `# coding` section with a nested `## tests`
section below it.

Unsupported scalar entries fail loudly instead of being silently ignored. This
keeps template mistakes visible during `apply`.

## Command Reference

Project lifecycle commands:

```bash
codexmgr setup
codexmgr apply
codexmgr apply --check
codexmgr apply --diff
codexmgr doctor
codexmgr status
```

`setup` creates `.codex/`, creates `.codex/codexmgr.toml` if missing, then runs
`apply`.

`apply` reads `.codex/codexmgr.toml`, resolves configured sources, writes
managed project files, and refreshes generated state.

`apply --check` exits with a failure if generated files are out of sync without
writing them. `apply --diff` also avoids writing and prints unified diffs for
the expected generated-file changes.

`doctor` checks project setup, home environment variables, project TOML syntax,
referenced snippets, enabled skills, enabled custom agents, enabled hook
bundles, enabled rules, and stale generated files.

`status` prints the resolved homes, configured snippets, skills, custom agents,
hooks, rules, and whether generated files are in sync.

Manager-home navigation:

```bash
codexmgr cd
codexmgr cd --path
codexmgr cd --explorer
codexmgr cd --terminal
```

`cd` launches a shell in `$CODEXMGR_HOME`. The flags print the path, open a file
explorer, or open a new terminal there.

AGENTS.md snippet commands:

```bash
codexmgr agentsmd list
codexmgr agentsmd show <name-or-template-path>
codexmgr agentsmd validate <name-or-template-path>
codexmgr agentsmd add [--no-sync] <name-or-template-path> [...]
codexmgr agentsmd remove [--no-sync] <name-or-template-path> [...]
codexmgr init-template agentsmd <name>
```

`agentsmd list` prints named templates from `$CODEXMGR_HOME/agentsmd` in sorted
order.

`agentsmd show` renders one template as `AGENTS.md` markdown without changing
project configuration. `agentsmd validate` loads and renders a template to catch
TOML or template-shape errors before adding it.

`agentsmd add` validates that the template exists before writing config.
Repeated adds keep one source entry.

`agentsmd remove` removes configured template sources and fails if a requested
source is not present.

`init-template agentsmd` creates a starter template under
`$CODEXMGR_HOME/agentsmd` and refuses to overwrite an existing template.

Shared resource commands:

```bash
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
```

`skill list`, `agents list`, `hooks list`, and `rules list` print available
resources and mark configured entries as enabled, disabled, or missing.

Enable commands validate manager-home sources when the source type must already
exist. Enable and disable lists stay mutually exclusive, and repeated commands
keep one entry.

Rules have one exception to exact mutual exclusion: a parent folder enable and a
child file or folder disable can intentionally coexist.

Package commands:

```bash
codexmgr package list
codexmgr package enable [--no-sync] <package-name> [...] [--profile <name> [...]]
codexmgr package disable [--no-sync] <package-name> [...] [--profile <name> [...]]
```

`package list` prints available `$CODEXMGR_HOME/packages/*/config.toml` entries
in sorted order.

`package enable` and `package disable` proxy to the underlying AGENTS.md,
custom-agent, skill, hook, and rule project-config mutations.

Codex wrapper command:

```bash
codexmgr codex <args...>
```

`codexmgr codex` applies the current project config, flattens
`.codex/config.toml` into `-c key=value` overrides, and forwards the remaining
arguments to the real `codex` command.

User-provided `-c` or `--config` overrides are merged after project config.
Scalar values replace earlier values, while list values append.

The wrapper can run with a just-in-time package/profile overlay without changing
`.codex/codexmgr.toml`. Put Codex arguments after `--` when using this syntax:

```bash
codexmgr codex --package repo-rules --profile strict python -- exec "review this"
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

## Development

Use a checkout when developing `codexmgr` itself.

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
