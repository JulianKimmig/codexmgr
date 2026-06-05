# TASK-003: Implement MCP Read Model, Validation, List, And Show

## Status

- Status: not-started
- Milestone: M02
- Dependencies: TASK-002
- Blocks: TASK-004, TASK-005, TASK-006

## Expected Current State

Round-trip user config infrastructure exists. Temporary Codex home tests can
load and write user config safely.

## Implementation Plan

1. Add an MCP module, for example `src/codexmgr/mcp_user_config.py`.
2. Implement loading and validating top-level `[mcp_servers]`.
3. Represent existing servers with id, transport, explicit enabled value,
   effective enabled state, and a safe display summary.
4. Add parser entries for:
   - `codexmgr mcp list`
   - `codexmgr mcp show <server-id>`
5. Add CLI dispatch through a thin helper module, for example
   `src/codexmgr/mcp_cli.py`.
6. Ensure list/show do not require project `.codex/`.
7. Redact raw `env` values and static `http_headers` values in show output.

## Expected Deliverables

- Read model and validation helpers.
- `mcp list` command.
- `mcp show` command.
- Tests for STDIO, HTTP, implicit enabled, disabled, missing config, missing id,
  invalid shapes, and redaction.

## Acceptance Criteria

- Existing servers under `[mcp_servers.<id>]` are listed.
- `enabled` missing is displayed as enabled implicit.
- `enabled = false` is displayed as disabled.
- `show` includes command/url and token env var names but not raw secret values.
- Invalid `[mcp_servers]` shapes fail with `CommandError`.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_user_config.py tests/test_mcp_cli.py
```

Then run the full suite:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest
```

## Edge Cases And Risks

- A server table might contain neither `command` nor `url`; list should show an
  invalid transport or fail according to the test-defined behavior.
- A server table might contain both `command` and `url`; this should be reported
  clearly.
- Raw secret redaction should be conservative.
- Keep parser additions short to avoid line-count pressure.

## Completion Evidence

Record:

- Command examples tested.
- Invalid-shape cases covered.
- Redaction behavior covered.
- Line-count output.

## Stop Conditions

Stop if the command surface cannot be added without pushing existing files above
300 lines; split parser/dispatch before continuing.
