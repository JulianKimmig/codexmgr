# Validation And Risk

## Test Strategy

Use behavior-first pytest tests with temporary `CODEX_HOME` directories. Tests
must not read or write the real `~/.codex/config.toml`.

Preferred test files:

- `tests/test_mcp_user_config.py`
- `tests/test_mcp_cli.py`
- `tests/test_mcp_validation_cli.py`
- Existing `tests/test_home_resolution_cli.py` can receive home-resolution
  coverage if that keeps test organization clearer.

Core verification command:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest
```

Dependency/update verification:

```bash
UV_CACHE_DIR=.cache/uv uv sync --group dev
UV_CACHE_DIR=.cache/uv uv run pytest
```

Line-count check:

```bash
wc -l src/codexmgr/*.py
```

## Task Validation Rules

- Every code-changing task starts with tests.
- Tests must use temporary `CODEX_HOME`.
- Tests must inspect resulting TOML behavior, not implementation internals.
- Mutating tests must assert unrelated config is preserved.
- Mutating tests must assert missing server ids fail.
- Parameter tests must assert no new server table is created.
- Secret-related tests must assert raw values are not printed by list/show.

## Milestone Validation Rules

M01:

- Config infrastructure can edit temporary user config without losing unrelated
  config.
- Dependency changes are locked and tests run.

M02:

- `mcp list` and `mcp show` produce stable, useful output.
- Invalid config shapes fail with actionable errors.

M03:

- Enable/disable and parameter mutation work for existing servers only.
- Scope guards prevent add/remove behavior.

M04:

- Documentation and help match implementation.
- Full test suite and line-count checks pass.

## Final Acceptance Checks

- `codexmgr mcp list` reads `CODEX_HOME/config.toml`.
- `codexmgr mcp enable <id>` writes `enabled = true` only for an existing server.
- `codexmgr mcp disable <id>` writes `enabled = false` only for an existing server.
- Parameter commands mutate only existing server tables and allowlisted fields.
- No command in this feature creates or deletes `[mcp_servers.<id>]`.
- User config comments and formatting are preserved by round-trip writes where
  the TOML library supports it.
- README explains the difference between this workflow and `codex mcp add`.
- Source files remain under 300 lines.

## Risk Register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| RISK-001: Real user config is mutated in tests | High | Inject temporary `codex_home` in all tests and add explicit safety tests. |
| RISK-002: Existing comments or formatting are destroyed | High | Use `tomlkit`; do not use the deterministic project TOML writer for user config mutation. |
| RISK-003: Command accidentally creates a new server | High | Centralize server lookup and fail if id is absent; test every mutating command for missing ids. |
| RISK-004: Literal API token is printed or stored casually | High | Default to env var references; redact list/show output; defer raw secret writes. |
| RISK-005: CLI file sizes exceed 300 lines | Medium | Add `mcp_user_config.py`, `mcp_cli.py`, and optional `mcp_validation.py`; keep parser/dispatch thin. |
| RISK-006: Global MCP workflow conflicts with project-oriented status/doctor | Medium | Keep `mcp validate` self-contained; avoid changing project `status` unless needed. |
| RISK-007: Codex schema evolves | Medium | Validate only fields this feature mutates; preserve unknown existing fields. |
| RISK-008: Dependency addition fails in restricted environment | Medium | Use uv; if dependency download is blocked, request network approval or replan around a round-trip edit strategy. |

## Security And Privacy Checks

- Do not read the real user config in tests.
- Do not print raw `env` values or static `http_headers` values.
- Do not expand environment variables.
- Do not start MCP commands.
- Do not call MCP URLs.
- Do not perform OAuth login.
- Avoid command examples that pass literal token values on the shell command
  line.

## Release Or Handoff Checks

- Record exact tests run and outcomes.
- Record line-count output.
- Record whether `tomlkit` was added and lockfile updated.
- Record any deferred parameter fields.
- Leave `git status` clean or explain unrelated pre-existing changes.
