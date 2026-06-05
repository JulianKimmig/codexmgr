# TASK-001: Establish MCP User Config Test Fixtures And Scope Guards

## Status

- Status: ready
- Milestone: M01
- Dependencies: none
- Blocks: TASK-002, TASK-003, TASK-004, TASK-005

## Expected Current State

The repository has pytest fixtures for temporary project directories and
temporary Codex homes. No MCP user-config tests exist. The real user
`~/.codex/config.toml` must not be read or written.

## Implementation Plan

1. Add behavior tests that define the safety expectations before source changes.
2. Extend test helpers only if needed to write and read temporary
   `codex_home/config.toml`.
3. Add tests proving MCP commands use the injected `codex_home` from
   `codexmgr.cli.main()`.
4. Add tests proving MCP mutating commands do not require project `.codex/`.
5. Add tests proving missing server ids fail instead of creating new server
   tables.
6. Keep tests focused on behavior and temporary files.

## Expected Deliverables

- New MCP test file with failing tests for the intended behavior.
- Optional shared fixture helpers for temporary user Codex config.
- No source implementation beyond minimal fixture support if needed.

## Acceptance Criteria

- Tests fail for missing implementation, not because fixtures are broken.
- Tests never reference the real home directory.
- Tests make it clear that add/remove server lifecycle is out of scope.
- Tests document that `CODEX_HOME/config.toml` is the target.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_user_config.py
```

The expected result before implementation is failing tests that describe the
missing MCP behavior.

## Edge Cases And Risks

- Avoid adding tests that assume comments can be preserved before the round-trip
  editor exists; those belong in TASK-002.
- Do not use monkeypatches to replace codexmgr source behavior.
- Do not inspect real user config even for discovery.

## Completion Evidence

Record:

- Test files added.
- Fixture helpers added.
- The failing test names and failure reason.

## Stop Conditions

Stop if a test cannot be written without reading the real user config.
