# TASK-007: Update README And User-Facing Documentation

## Status

- Status: not-started
- Milestone: M04
- Dependencies: TASK-006
- Blocks: TASK-008

## Expected Current State

The MCP command surface is implemented and tested. Command names and behavior
are stable.

## Implementation Plan

1. Add MCP user-config management to the README tool summary.
2. Add a "User MCP Servers" section explaining:
   - target file is `CODEX_HOME/config.toml`.
   - default is `~/.codex/config.toml`.
   - commands operate only on existing servers.
   - `codex mcp add` or manual editing remains the server creation workflow.
3. Document enable/disable examples.
4. Document safe token/env reference examples.
5. Document that literal token writes are not supported in v1.
6. Update command list.
7. Mention no project `.codex/` is required for MCP commands.

## Expected Deliverables

- README updates.
- Any necessary help text adjustments discovered while documenting.

## Acceptance Criteria

- README matches implemented command names exactly.
- README clearly says add/remove server lifecycle is out of scope.
- README examples avoid literal API token values.
- README distinguishes user config management from project `apply`.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest
```

Manually inspect:

```bash
UV_CACHE_DIR=.cache/uv uv run codexmgr --help
UV_CACHE_DIR=.cache/uv uv run codexmgr mcp --help
```

## Edge Cases And Risks

- Do not document commands that were deferred.
- Do not imply `codexmgr mcp` manages plugin-provided MCP servers.
- Do not suggest putting literal tokens in commands.

## Completion Evidence

Record:

- README sections changed.
- Help commands checked.
- Tests run and results.

## Stop Conditions

Stop if documentation reveals a mismatch between implemented behavior and the
requested scope; replan before adjusting scope.
