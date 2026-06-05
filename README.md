# codexmgr

`codexmgr` manages project-local Codex configuration from reusable templates.
It keeps hand-written project instructions in `AGENTS.md` and generated Codex
configuration in `.codex/` synchronized from a small declarative
`.codex/codexmgr.toml` file.

The tool is intentionally narrow:

- compose reusable AGENTS.md instruction fragments
- enable or disable Codex skills per project
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
- `.codex/codexmgr.lock`: resolved template and skill state written by `apply`
- `.codex/config.toml`: Codex config updated with `[[skills.config]]` entries
- `AGENTS.md`: project instructions, with only the managed block replaced

The managed AGENTS.md block is:

```markdown
<!-- BEGIN CODEXMGR GENERATED -->
<!-- END CODEXMGR GENERATED -->
```

Manual content outside this block is preserved. If the block is missing,
`codexmgr` appends it. If `AGENTS.md` is missing, `codexmgr` creates it.

## Project Configuration

`.codex/codexmgr.toml` supports AGENTS.md templates and skill state:

```toml
[agents_md]
src = ["coding", "/absolute/or/project-relative/template.toml"]

[skills]
enabled = ["review-helper"]
disabled = ["experimental-skill", "skills/local-disabled"]
```

Named AGENTS.md templates resolve from `$CODEXMGR_HOME/agentsmd/<name>.toml`.
Path-like template values resolve relative to the project unless they are
absolute paths.

Named skills resolve from `$CODEX_HOME/skills/<name>/SKILL.md`. If `CODEX_HOME`
is unset, `~/.codex` is used. Path-like skill values resolve to either a
`SKILL.md` file or a directory containing `SKILL.md`. Missing skills are written
as name-based entries so Codex can resolve them later.

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
codexmgr cd [--path | --explorer | --terminal]
codexmgr agentsmd list
codexmgr agentsmd add [--no-sync] <name-or-template-path>
codexmgr agentsmd remove [--no-sync] <name-or-template-path>
codexmgr skill enable [--no-sync] <name-or-skill-path>
codexmgr skill disable [--no-sync] <name-or-skill-path>
codexmgr codex <args...>
```

`setup` creates `.codex/` in the current project.

`apply` reads `.codex/codexmgr.toml`, resolves configured sources, writes
`.codex/codexmgr.lock`, updates `.codex/config.toml` skill entries when a
`[skills]` table is configured, and refreshes the generated `AGENTS.md` block
when `[agents_md]` is configured.

`cd` launches a shell in `$CODEXMGR_HOME`, similar to `chezmoi cd`. Use
`codexmgr cd --path` to print only the path, `codexmgr cd --explorer` to open
the directory in a file explorer, and `codexmgr cd --terminal` to open a new
terminal there.

`agentsmd list` prints the named templates available under
`$CODEXMGR_HOME/agentsmd` in sorted order.

`agentsmd add` validates that the template exists before writing config.
Repeated adds keep one source entry.

`agentsmd remove` removes a configured template source and fails if the source
is not present.

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
template rendering, TOML writing, skill resolution, Codex command generation,
home-directory resolution, and package metadata.

## Release Notes

The GitHub workflow runs the test matrix on Python 3.11, 3.12, and 3.13 across
Linux, Windows, and macOS. The publish workflow builds and publishes to PyPI
when the version in `pyproject.toml` differs from the latest published version.
