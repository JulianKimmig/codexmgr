# TASK-002: Add Round-Trip User Codex Config Infrastructure

## Status

- Status: not-started
- Milestone: M01
- Dependencies: TASK-001
- Blocks: TASK-003, TASK-004, TASK-005

## Expected Current State

TASK-001 has established tests and fixtures for temporary `CODEX_HOME/config.toml`.
The current `toml_io.py` writer is deterministic but not suitable for preserving
comments in user-owned global config.

## Implementation Plan

1. Add `tomlkit` as a dependency with uv.
2. Add a path helper such as `global_codex_config_path(codex_home: Path)`.
3. Add a new module for user config IO, for example
   `src/codexmgr/user_config.py`.
4. Implement round-trip load/write helpers for `CODEX_HOME/config.toml`.
5. Convert TOML parse errors into `CommandError`.
6. Preserve comments and unrelated values in tests.
7. Keep the existing deterministic `toml_io.py` unchanged for generated project
   files.

## Expected Deliverables

- `tomlkit` added to `pyproject.toml` and `uv.lock`.
- New user config helper module with docstrings.
- Tests for missing config, invalid TOML, preserving comments, and preserving
  unrelated values.

## Acceptance Criteria

- User config writes do not drop unrelated keys.
- User config writes preserve comments in representative fixtures.
- Missing `config.toml` produces clear read-only/list behavior and clear
  mutating-command errors.
- Existing project-generated TOML behavior is unchanged.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv sync --group dev
UV_CACHE_DIR=.cache/uv uv run pytest tests/test_mcp_user_config.py
UV_CACHE_DIR=.cache/uv uv run pytest
```

Also run:

```bash
wc -l src/codexmgr/*.py
```

## Edge Cases And Risks

- Dependency download may need network approval.
- Round-trip libraries preserve formatting but can still normalize some trivia;
  tests should cover representative comments without over-specifying every
  whitespace detail.
- Do not rewrite existing generated TOML code to use `tomlkit`.

## Completion Evidence

Record:

- Dependency command used.
- Files changed.
- Tests run and result.
- Line-count output.

## Stop Conditions

Stop if adding `tomlkit` is rejected or impossible; replan before attempting a
manual TOML patcher.
