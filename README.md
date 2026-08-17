# codexmgr

`codexmgr` manages reusable Codex project setup. Keep shared `AGENTS.md`
snippets, skills, hooks, custom agents, rule files, packages, and reusable MCP
source files in one manager home, then sync the selected pieces into each
project from `.codex/codexmgr.toml`.

The tool is for people who use Codex in several repositories and do not want to
copy the same agent instructions by hand. When a shared rule changes, update it
once in `$CODEXMGR_HOME` and apply it wherever that project has opted in.

Use `codexmgr` when a project should:

- build `AGENTS.md` from reusable instruction snippets
- share skills, hooks, custom agents, and rule files across repositories
- enable packaged Codex setups made from those reusable pieces
- keep reusable MCP server definitions out of the user-level Codex config
- check whether generated Codex files match the project config
- run `codex` with the project `.codex` directory as its local Codex home

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
runs `apply`. Existing project config is preserved. Apply also creates or
refreshes codexmgr's managed block in `.codex/.gitignore`.

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

- `.codex/.gitignore`: preserves manual rules outside its managed block,
  ignores every unknown `.codex` entry by default, and explicitly exposes the
  codexmgr-owned files and directories listed below
- `.codex/codexmgr.lock`: resolved AGENTS.md, agent, skill, hook, rule, and MCP
  state
- `.codex/config.toml`: project-local Codex config, including generated
  `[[skills.config]]` entries and `[mcp_servers.<id>]` server definitions
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

Known managed, source-backed skill files, reusable rule files, custom-agent
TOML files, and hook support files receive additional local-edit protection. If
one differs from its reusable source, interactive apply asks whether to keep
the local file for this run, overwrite it from the source, update the shared
source from the local file, or abort. Keeping local is temporary and prompts
again on the next apply. Updating a source warns that other projects may share
it and validates the local content when that resource has a validator.

Generated and composed outputs do not use these choices: the managed
`AGENTS.md` block, `.codex/config.toml`, merged `.codex/hooks.json`,
`.codex/.gitignore`, and `.codex/codexmgr.lock` keep their existing generation
behavior. Extra local files in skill and hook overlay directories remain
untouched. The project-local managed copy conflicts contract records the full
scope and implementation map.

## Project Configuration

`.codex/codexmgr.toml` can opt into each resource type independently. A minimal
file may only contain `[agents_md]`; larger projects can add skills, custom
agents, hooks, reusable rules, and MCP sources or overlays as needed. Package commands
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
[mcp]
enabled = ["browsermcp"]
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

Bare skill names resolve across the project `.agents/skills`,
`$CODEXMGR_HOME/skills`, and `$CODEX_HOME/skills` stores. If the same folder
name exists in more than one store, apply fails and asks for an explicit path.
The project copy recorded for an enabled `$CODEXMGR_HOME` skill is recognized
as a managed mirror and does not create a false collision on later applies.

Enabled skills from `$CODEXMGR_HOME` are copied into `.agents/skills/<name>` on
every apply. Differing files in a known managed copy use the per-target
conflict choices, while the overlay preserves extra local files.
Path-like skill values can point to a `SKILL.md` file or a directory containing
`SKILL.md`; a path-like value that does not exist is an error.

Project-local and copied manager-home skills generate portable `name` selectors
using the `name` value in their `SKILL.md` YAML frontmatter. Selected skills in
those stores must therefore have valid frontmatter and a non-empty name. Apply
also fails if two discoverable skills declare the same generated name. Skills
resolved directly from `$CODEX_HOME` and explicit path references keep absolute
`path` selectors because those sources are machine-specific or explicitly
requested. Missing bare names remain name-based entries so Codex can resolve
them later from another installed source.

Managed skill-copy lock entries use the logical source `codexmgr_home` and a
project-relative `.agents/skills/<name>` target. Apply accepts legacy absolute
copy entries and rewrites them in this portable form, so moving or cloning a
project does not churn generated skill config or lock state.

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

Rule listings are grouped by folder. `codexmgr rules list` prints an indented
tree, while the TUI Rules screen shows the same refs in a collapsible tree.

File rule refs copy one file. Extensionless refs prefer an existing `<ref>.md`.
Enabled refs expand first, then disabled file or folder refs remove entries from
that candidate set.

First-time rule applies refuse to overwrite unmanaged `.rules/...` files. This
keeps existing project-local rules from being replaced accidentally. The
per-target conflict choices apply after a target is a known managed copy.

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
packages, and reusable MCP sources in selectable lists. Rules are shown
in a collapsible folder tree.

Changes are staged in memory while you navigate. Press `s` to save; the save
writes `.codex/codexmgr.toml` once and runs `apply` once unless `--no-sync` was
used. When apply finds a known managed direct-copy conflict, the TUI offers the
same `keep-local`, `overwrite-local`, `update-source`, and `abort` choices as
the interactive CLI.

For resources with explicit enable and disable lists, `space` cycles the
highlighted row through available, enabled, and disabled states. Package
profiles appear as separate selectable rows under their package. In the Rules
tree, cycling a file or folder node updates the full canonical rule ref behind
that basename label.

```bash
codexmgr tui
codexmgr tui --no-sync
codexmgr tui --show-diff
```

The dashboard shows generated-file sync state. By default it lists stale
generated paths; with `--show-diff`, it shows unified diffs for the staged
configuration.

MCP editing in the TUI is intentionally limited to loading and unloading
reusable `$CODEXMGR_HOME/mcp/*.toml` sources. Advanced per-server overlay fields
remain available through the `codexmgr mcp ...` commands or direct
`.codex/codexmgr.toml` edits.

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
codexmgr apply --resolve <target-path> <keep-local|overwrite-local|update-source>
codexmgr apply --check
codexmgr apply --diff
codexmgr doctor
codexmgr status
```

`setup` creates `.codex/`, creates `.codex/codexmgr.toml` if missing, then runs
`apply`.

`apply` reads `.codex/codexmgr.toml`, resolves configured sources, writes
managed project files, and refreshes generated state.

For scripts and other noninteractive use, repeat `--resolve` with a target path
and action for every known managed, source-backed copy conflict. For example:

```bash
codexmgr apply \
  --resolve .agents/skills/review/SKILL.md keep-local \
  --resolve .rules/python/testing.md update-source
```

The available actions are `keep-local`, `overwrite-local`, and
`update-source`. These resolutions apply only to the current invocation; an
unresolved target makes noninteractive apply fail before writes.

`apply --check` exits with a failure if generated files are out of sync without
writing them. `apply --diff` also avoids writing and prints unified diffs for
the expected generated-file changes. Both modes remain read-only when a managed
copy differs from its source. A noninteractive `apply` requires an explicit
resolution for each conflicting target and fails before writes when any target
is unresolved.

The `.codex/.gitignore` managed block uses a default-ignore rule rather than a
list of known runtime filenames. New caches, databases, sessions, and other
state created by future Codex versions therefore remain outside Git without a
codexmgr update. Project configuration, custom agents, and hook support files
remain visible to Git.

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

`skill list`, `agents list`, and `hooks list` print available resources and
mark configured entries as enabled, disabled, or missing. `rules list` prints
the same state in an indented folder hierarchy.

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
codexmgr codex --simple <args...>
```

By default, `codexmgr codex` applies the current project config, launches the
real `codex` command with `CODEX_HOME` set to
`<project>/.codex/.runtime`, and forwards Codex arguments unchanged. For a
trusted project, Codex discovers the tracked `.codex/config.toml` as its
project configuration independently of `CODEX_HOME`. This keeps generated MCP
servers and other shared project settings in Git while mutable Codex state is
written below the ignored `.codex/.runtime` directory. User-provided `-c` and
`--config` arguments retain their normal Codex behavior.

The wrapper links the global authentication file into
`.codex/.runtime/auth.json`. It uses `CODEX_GLOBAL_AUTH` when that variable is
non-empty and otherwise uses `$HOME/.codex/auth.json`. A missing auth source
produces a warning but does not stop Codex, which can then authenticate within
the project runtime home.

Use `--simple` immediately after `codex` to run the basic command without
applying project state, changing the child `CODEX_HOME`, or managing an auth
link. This launch wrapper is intentionally CLI-only because the TUI does not
embed or proxy external terminal sessions.

The wrapper can run with a just-in-time package/profile overlay without changing
`.codex/codexmgr.toml`. Put Codex arguments after `--` when using this syntax:

```bash
codexmgr codex --package repo-rules --profile strict python -- exec "review this"
```

## Project MCP Sources

`codexmgr mcp ...` loads reusable MCP definitions from `$CODEXMGR_HOME/mcp`
into project-local configuration:

- reusable source state is stored in `.codex/codexmgr.toml` under `[mcp]`
- per-project server overlays are stored under `[mcp.servers.<id>]`
- `apply` writes generated server definitions into `.codex/config.toml` under
  `[mcp_servers.<id>]`
- `$CODEX_HOME/config.toml` and `~/.codex/config.toml` are never modified

Mutating MCP commands require a project `.codex/` directory and run `apply`
automatically unless `--no-sync` is passed.

Create reusable source files in the same `mcp_servers` shape Codex reads from
`config.toml`:

```toml
# ~/.codexmgr/mcp/browsermcp.toml
[mcp_servers.browsermcp]
command = "browsermcp"
args = ["--port", "3000"]
env_vars = ["BROWSERMCP_TOKEN"]
```

List reusable sources and show project state:

```bash
codexmgr mcp list
codexmgr mcp show browsermcp
codexmgr mcp validate
```

Enable or disable reusable sources for the current project:

```bash
codexmgr mcp enable browsermcp context7
codexmgr mcp disable browsermcp
```

`disable` unloads the source from `[mcp].enabled`. It does not keep a generated
server definition with `enabled = false`.

Use `[mcp.servers.<id>]` for project-local overlays. Overlays merge after source
files, so they can override or add fields:

```toml
[mcp]
enabled = ["browsermcp"]

[mcp.servers.browsermcp]
enabled = false
bearer_token_env_var = "BROWSERMCP_TOKEN"
```

Update common token and environment references from the CLI:

```bash
codexmgr mcp set-token-env figma FIGMA_TOKEN
codexmgr mcp add-env-var context7 CONTEXT7_TOKEN
codexmgr mcp remove-env-var context7 CONTEXT7_TOKEN
codexmgr mcp set-env-header figma Authorization FIGMA_AUTH_HEADER
codexmgr mcp unset-env-header figma Authorization
```

Set a small allowlist of overlay fields from TOML literals:

```bash
codexmgr mcp set-field context7 required true
codexmgr mcp set-field context7 enabled_tools '["search", "open"]'
codexmgr mcp set-field context7 default_tools_approval_mode '"prompt"'
```

Supported `set-field` names are `required`, `startup_timeout_sec`,
`tool_timeout_sec`, `enabled_tools`, `disabled_tools`, and
`default_tools_approval_mode`.

Source files and hand-written overlays can use the full Codex `mcp_servers`
shape. Prefer environment variable references such as `bearer_token_env_var`,
`env_vars`, and `env_http_headers` for secrets.

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
