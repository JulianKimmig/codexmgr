# Decision Log

## DEC-001: Direct User Config Target

- Decision: MCP commands in this plan edit `CODEX_HOME/config.toml`.
- Reason: The updated user request specifically asks to turn MCP servers on or
  off in `~/.codex/config.toml`.
- Consequence: This feature is separate from project `apply` and
  `.codex/codexmgr.toml`.

## DEC-002: Round-Trip TOML Editing

- Decision: Use a round-trip TOML library, preferably `tomlkit`, for user config
  mutation.
- Reason: The current deterministic writer is appropriate for generated files
  but would rewrite user-owned global config and drop comments.
- Consequence: Implementation must add and lock a dependency, or replan if the
  dependency is rejected.

## DEC-003: No Add Or Remove Server Lifecycle

- Decision: Do not implement `mcp add` or `mcp remove`.
- Reason: The user explicitly wants server creation/removal to happen the
  traditional way.
- Consequence: Every mutating command must fail if the server id does not
  already exist.

## DEC-004: Safe Parameter Mutation

- Decision: Parameter mutation is allowlisted and defaults to env var
  references rather than raw secrets.
- Reason: API tokens should not be normalized as command-line literal values or
  printed in output.
- Consequence: V1 should include `set-token-env`, env var forwarding, env-header
  mutation, and non-secret scalar/list fields. Raw `env` writes are deferred.

## DEC-005: Project Status Is Not The Primary UI

- Decision: Keep MCP user-config diagnostics under the `mcp` command group.
- Reason: Existing `status` and `doctor` are project-oriented and require
  `.codex/codexmgr.toml`.
- Consequence: Add `codexmgr mcp validate` instead of forcing global MCP state
  into project status in v1.

## DEC-006: Preserve Unknown Server Fields

- Decision: Preserve unknown existing MCP fields and only validate fields this
  feature reads or writes.
- Reason: Codex's MCP schema may evolve, and this feature should not destroy
  or reject unrelated server configuration when only toggling `enabled`.
- Consequence: Validation is strict for shape and mutated fields, but not a full
  schema gate for all possible Codex MCP options.
