# TASK-005: Implement Safe Parameter Mutation For Existing MCP Servers

## Status

- Status: not-started
- Milestone: M03
- Dependencies: TASK-004
- Blocks: TASK-006, TASK-007

## Expected Current State

Enable/disable works for existing servers and the mutation helper can safely
locate and write one server table.

## Implementation Plan

1. Write tests for parameter commands before implementing them.
2. Add token/env-reference commands:
   - `codexmgr mcp set-token-env <server-id> <ENV_VAR>`
   - `codexmgr mcp add-env-var <server-id> <ENV_VAR>`
   - `codexmgr mcp remove-env-var <server-id> <ENV_VAR>`
   - `codexmgr mcp set-env-header <server-id> <HEADER> <ENV_VAR>`
   - `codexmgr mcp unset-env-header <server-id> <HEADER>`
3. Add allowlisted general field command if needed:
   - `codexmgr mcp set-field <server-id> <field> <toml-value>`
4. Restrict `set-field` to non-secret known fields:
   - `required`
   - `startup_timeout_sec`
   - `tool_timeout_sec`
   - `enabled_tools`
   - `disabled_tools`
   - `default_tools_approval_mode`
5. Parse `toml-value` as TOML for `set-field`.
6. Validate field-specific types and values.
7. Preserve existing server tables and comments.
8. Do not implement raw `env` value writes in v1.

## Expected Deliverables

- Safe parameter mutation commands for existing servers.
- Field allowlist and validators.
- Tests covering happy paths, invalid types, missing ids, and secret-safety.

## Acceptance Criteria

- Token command sets `bearer_token_env_var` to the given env var name.
- Env var commands update `env_vars` without duplicates.
- Env header commands update `env_http_headers` maps.
- `set-field` rejects unknown fields.
- Commands do not create or remove server tables.
- Commands do not accept raw API token values as a special happy path.
- Output does not print raw secret-like values.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_cli.py
UV_CACHE_DIR=.cache/uv uv run pytest
```

## Edge Cases And Risks

- `env_vars` can contain strings and inline tables. Adding/removing a string env
  var must preserve existing table entries.
- Header names can contain hyphens; use parsed TOML keys and round-trip APIs.
- `toml-value` parsing can surprise users. Error messages should show expected
  examples.
- Raw token storage may be requested later; keep this out of v1 unless the user
  explicitly replans.

## Completion Evidence

Record:

- Parameter commands implemented.
- Fields supported.
- Fields explicitly deferred.
- Tests run and results.

## Stop Conditions

Stop and ask before implementing literal token writes, raw `env` writes, or
static `http_headers` value writes.
