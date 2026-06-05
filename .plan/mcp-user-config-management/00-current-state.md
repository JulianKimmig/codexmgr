# Current State

## Product Interpretation

`codexmgr` currently manages project-local Codex configuration. This plan extends
it with a separate MCP user-config workflow that directly edits the Codex user
config file at `CODEX_HOME/config.toml`, defaulting to `~/.codex/config.toml`.

The feature is intentionally not a full MCP manager. It should operate on
already-configured MCP server entries and should not create or delete server
definitions.

## Existing Repository State

- Package: Python CLI package named `codexmgr`.
- Package manager: `uv`.
- Test runner: `pytest`, configured in `pytest.toml`.
- Current source layout: `src/codexmgr/*.py`.
- Current source file limit from project instructions: source files must remain
  under 300 lines.
- Existing path helper: `paths.global_codex_dir()` resolves `CODEX_HOME` or
  `~/.codex`.
- Existing TOML IO: `toml_io.py` can parse TOML and emit deterministic TOML, but
  it does not preserve comments or formatting.
- Existing CLI injection: tests can pass a temporary `codex_home` into
  `codexmgr.cli.main()`.
- Existing project pipeline: `apply`, `status`, and `doctor` currently require
  project `.codex/codexmgr.toml`.

## User Goals And Success Criteria

Primary success criteria:

- `codexmgr mcp list` shows existing MCP servers from `CODEX_HOME/config.toml`.
- `codexmgr mcp enable <server-id>` sets `mcp_servers.<server-id>.enabled = true`.
- `codexmgr mcp disable <server-id>` sets `mcp_servers.<server-id>.enabled = false`.
- Enable/disable commands fail if the server id does not already exist.
- Commands preserve unrelated Codex config and existing MCP server fields.
- Commands do not require a project `.codex/` directory.

Optional parameter success criteria:

- `codexmgr` can update a small allowlist of existing-server parameters.
- Token-oriented commands store environment variable names by default, not raw
  token values.
- Parameter commands fail when the target server does not exist.
- Parameter commands do not create or delete MCP server tables.

## Scope

In scope:

- Global/user Codex config path resolution through `CODEX_HOME`.
- Read-only MCP listing and inspection.
- Enable/disable mutation for existing `[mcp_servers.<id>]` tables.
- Safe parameter mutation for existing servers.
- Validation of the relevant MCP config shape before writing.
- Round-trip preservation of user config comments and formatting as much as
  practical.
- README and help text explaining this workflow.

Out of scope:

- Adding MCP server definitions.
- Removing MCP server definitions.
- Project-local generated MCP config through `.codex/codexmgr.toml`.
- Managing plugin-provided MCP servers under `[plugins.*.mcp_servers.*]`.
- Running MCP servers.
- Calling MCP HTTP URLs.
- OAuth login flows.
- Reading, expanding, or validating actual secret values.
- Editing `auth.json`, histories, logs, or other Codex state files.

## Constraints And Instructions

- Use TDD: tests first for each code change.
- Tests should verify behavior, not source-code internals.
- Do not mock codexmgr source code. Use temporary config files and injected home
  paths.
- Use `UV_CACHE_DIR=.cache/uv uv run pytest` for verification.
- When adding dependencies, use uv and update lock data intentionally.
- Keep source files below 300 lines by adding MCP-specific modules.
- Every new Python source file, class, function, and method needs a docstring.
- Avoid default fallbacks that hide broken config. Missing or malformed target
  MCP data should fail with actionable errors for mutating commands.

## Assumptions

- It is acceptable to add `tomlkit` for round-trip TOML editing. This avoids
  rewriting the user's whole `~/.codex/config.toml` and losing comments.
- `enabled` missing on an existing MCP server means Codex treats the server as
  enabled. `list` and `show` should display this as enabled with an implicit
  marker, while `enable` should write `enabled = true` explicitly.
- API-token changes should mean setting token environment variable references,
  such as `bearer_token_env_var`, not writing literal tokens.
- Raw secret-value writing is deferred unless the user explicitly requests it
  later.
- The real `~/.codex/config.toml` should not be read during tests or planning.

## Unknowns

- Q-001: Whether `tomlkit` is acceptable as a runtime dependency.
  - Status: assumable.
  - Revisit trigger: user rejects adding a dependency or dependency installation
    is blocked.
- Q-002: Whether raw secret values should ever be supported.
  - Status: non-blocking.
  - Revisit trigger: user explicitly requests writing literal tokens.
- Q-003: Whether MCP commands should also support project-local config later.
  - Status: out of scope for this plan.
  - Revisit trigger: user asks for project-local MCP management again.
