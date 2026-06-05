# TASK-006: Add MCP Validation Diagnostics And Command Help Polish

## Status

- Status: not-started
- Milestone: M04
- Dependencies: TASK-005
- Blocks: TASK-007, TASK-008

## Expected Current State

Read, toggle, and safe parameter mutation commands exist. Validation helpers are
available in the MCP module.

## Implementation Plan

1. Add tests for `codexmgr mcp validate`.
2. Implement `codexmgr mcp validate [server-id]`.
3. Validate only deterministic local config shape:
   - top-level `mcp_servers` table shape.
   - existing server table shape.
   - `enabled` boolean when present.
   - mutated fields supported by this feature.
   - transport summary from `command` or `url`.
4. Add warnings for:
   - raw `env` values present.
   - static `http_headers` present.
   - missing token env var references if checking current environment is kept
     deterministic enough.
5. Polish argparse help text for all MCP commands.
6. Keep project `doctor` unchanged unless there is a small, clearly useful
   integration point that does not require project config.

## Expected Deliverables

- `mcp validate` command.
- Validation output tests.
- Help text matching implemented commands.

## Acceptance Criteria

- `mcp validate` exits zero for valid existing config.
- `mcp validate <id>` validates one existing server.
- Validation fails clearly for missing ids and invalid shapes.
- Validation does not start servers or make network calls.
- Help text does not advertise add/remove server lifecycle.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_validation_cli.py tests/test_mcp_cli.py
UV_CACHE_DIR=.cache/uv uv run pytest
```

## Edge Cases And Risks

- Do not make validation a full Codex schema gate. Unknown existing fields should
  be preserved and at most warned about.
- Environment-variable checks can be flaky; if included, treat them as warnings
  and test with controlled environment values.

## Completion Evidence

Record:

- Validation behavior and warning categories.
- Help text checked.
- Tests run and results.

## Stop Conditions

Stop if validation would need to start commands, connect to URLs, or inspect
OAuth state.
