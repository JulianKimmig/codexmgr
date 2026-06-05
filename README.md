# codexmgr

`codexmgr` sets up project-local Codex configuration from reusable TOML
instruction templates.

## Commands

```bash
codexmgr setup
codexmgr apply
codexmgr codex --help
codexmgr agentsmd add coding
codexmgr agentsmd add /path/to/template.toml
codexmgr agentsmd remove coding
codexmgr skill enable skill-name
codexmgr skill disable /path/to/skill
```

`setup` creates `.codex/` in the current project.
`apply` reads `.codex/codexmgr.toml`, resolves configured sources, writes
`.codex/codexmgr.lock`, and refreshes the managed block in the project root
`AGENTS.md`. It also writes skill enablement state to `.codex/config.toml`.
`codex` runs the normal `codex` command with all arguments forwarded, while
prepending `-c key=value` overrides for the complete `.codex/config.toml`.

Named templates are loaded from `$CODEX_HOME/agentsmd/<name>.toml`. If
`CODEX_HOME` is not set, the default is `~/.codex`.

Adding a template records its source in `.codex/codexmgr.toml`:

```toml
[agents_md]
src = ["coding", "/path/to/template.toml"]

[skills]
enabled = ["skill-name"]
disabled = ["/path/to/skill"]
```

Rendered markdown is written only when `apply` runs. It updates the project
root `AGENTS.md` inside this managed block:

```markdown
<!-- BEGIN CODEXMGR GENERATED -->
<!-- END CODEXMGR GENERATED -->
```

Manual content outside that block is preserved. If the block does not exist,
`codexmgr` appends it to `AGENTS.md`; if `AGENTS.md` does not exist, it creates
the file.

Skills are also resolved only when `apply` runs. Named skills resolve from
`$CODEX_HOME/skills/<name>/SKILL.md`; path-like values resolve to a full
`SKILL.md` path. If a skill cannot be resolved to a file, its configured value
is written as `name` instead. The entries are written to both
`.codex/config.toml` and `.codex/codexmgr.lock`:

```toml
[[skills.config]]
path = "/resolved/full/path/SKILL.md"
enabled = true

[[skills.config]]
name = "unresolved-skill"
enabled = false
```

## Tests

```bash
UV_CACHE_DIR=.cache/uv uv run pytest
```
