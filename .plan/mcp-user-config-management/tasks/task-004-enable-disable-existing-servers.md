# TASK-004: Implement Enable And Disable For Existing MCP Servers

## Status

- Status: not-started
- Milestone: M03
- Dependencies: TASK-003
- Blocks: TASK-005, TASK-006

## Expected Current State

`codexmgr mcp list` and `codexmgr mcp show` can read existing user MCP config.
The CLI has an `mcp` command group.

## Implementation Plan

1. Write tests first for:
   - enabling an explicitly disabled existing server.
   - disabling an explicitly enabled existing server.
   - disabling an implicitly enabled existing server.
   - failure when the server id is absent.
   - preserving comments, unrelated config, and all other server fields.
2. Add parser entries:
   - `codexmgr mcp enable <server-id>`
   - `codexmgr mcp disable <server-id>`
3. Implement a shared mutation helper that:
   - loads user config.
   - locates an existing server table.
   - sets only `enabled`.
   - writes round-trip config.
4. Return concise success messages.
5. Do not call project `apply`.

## Expected Deliverables

- Enable/disable commands.
- Shared existing-server mutation helper.
- Behavior tests covering preservation and absent-server failures.

## Acceptance Criteria

- `enable` writes `enabled = true`.
- `disable` writes `enabled = false`.
- Commands never create `[mcp_servers.<id>]`.
- Commands fail when `config.toml` is missing.
- Commands fail when `[mcp_servers]` is missing or not a table.
- Commands preserve other fields and comments.
- Commands do not require project setup.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_user_config.py tests/test_mcp_cli.py
UV_CACHE_DIR=.cache/uv uv run pytest
```

## Edge Cases And Risks

- If a server id requires TOML quoting, ensure lookup uses parsed keys, not
  string path splitting.
- If `enabled` exists with a non-boolean value, fail instead of overwriting
  silently.
- Success messages should not include secret fields.

## Completion Evidence

Record:

- Tests added.
- Example before/after TOML fixture behavior.
- Commands run and results.

## Stop Conditions

Stop if enable/disable would require creating a server table. That violates the
explicit non-goal.
