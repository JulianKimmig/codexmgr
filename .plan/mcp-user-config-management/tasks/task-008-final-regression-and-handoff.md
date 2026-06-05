# TASK-008: Run Final Regression, Line-Count, And Handoff Checks

## Status

- Status: not-started
- Milestone: M04
- Dependencies: TASK-007
- Blocks: none

## Expected Current State

All MCP user-config functionality and documentation are implemented.

## Implementation Plan

1. Run the full test suite.
2. Run line-count checks for source files.
3. Inspect `git status --short`.
4. Verify generated docs and tests do not touch real `~/.codex/config.toml`.
5. Verify no `mcp add` or `mcp remove` server lifecycle commands were added.
6. Commit completed work if following the project guideline for a clean git
   status and the user has not directed otherwise.
7. Update this plan's task statuses and completion evidence.

## Expected Deliverables

- Final validation evidence.
- Clean or clearly explained git status.
- Updated handoff notes.

## Acceptance Criteria

- `UV_CACHE_DIR=.cache/uv uv run pytest` passes.
- All source files remain below 300 lines.
- README and help text match implemented commands.
- Real user config was not touched by tests.
- Worktree state is clean or unrelated changes are explicitly reported.

## Validation

Run:

```bash
UV_CACHE_DIR=.cache/uv uv run pytest
wc -l src/codexmgr/*.py
git status --short
```

## Edge Cases And Risks

- Pre-existing unrelated worktree changes may exist. Do not revert them.
- Dependency updates may modify `uv.lock`; include them intentionally.
- If committing, avoid including unrelated local changes.

## Completion Evidence

Record:

- Final test output summary.
- Line-count output.
- Git status summary.
- Commit SHA if a commit is created.

## Stop Conditions

Stop if tests fail for reasons unrelated to the MCP change and cannot be
resolved without touching unrelated code.
