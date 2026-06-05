# Appendix: Prior MCP Thought Synthesis

## Files Used

This plan used all files under `.thoughts/mcp-server-management/`:

- `clarification.md`
- `perspectives.md`
- `summary.md`
- `results/agent-1.md`
- `results/agent-2.md`
- `results/agent-3.md`

## What Carries Forward

The earlier analysis remains useful for these points:

- MCP config lives under `[mcp_servers.<id>]`.
- MCP entries are security-sensitive because they can start commands, forward
  environment variables, and authenticate HTTP servers.
- codexmgr should not start MCP servers or touch network resources for config
  management.
- Existing TOML shape should be preserved rather than replaced wholesale.
- CLI, validation, and health behavior should live in MCP-specific modules to
  keep source files below the project line limit.
- Tests should cover invalid shape, missing server ids, secrets, and formatting.

## What Changes From The Earlier Proposal

The earlier design proposal scoped MCP management to project-local generated
config. The updated user request changes the target:

- Previous target: `.codex/codexmgr.toml` generating `.codex/config.toml`.
- New target: direct edits to user Codex config at `CODEX_HOME/config.toml`.
- Previous CLI included add/remove lifecycle.
- New CLI must not add or remove MCP servers.
- Previous ownership model used `.codex/codexmgr.lock`.
- New model does not need a lockfile because it mutates one existing user-owned
  config file in place.

## Design Lessons Adapted

Preservation:

- The plan keeps the earlier preservation principle, but applies it to
  round-trip user config editing instead of generated project config merging.

Security:

- The plan keeps the earlier secret-handling stance and makes env var references
  the default path for token parameters.

Diagnostics:

- The plan keeps deterministic diagnostics and rejects runtime checks that start
  servers or make network calls.

Modularity:

- The plan keeps the recommendation to add dedicated MCP modules instead of
  expanding `skills.py`, `cli.py`, or `health.py`.

## Relevant Official Codex Facts

From the fetched Codex docs reflected in the thought artifacts:

- Codex stores MCP config in `config.toml`.
- The default user config path is `~/.codex/config.toml`, configurable through
  `CODEX_HOME`.
- Servers are configured under `[mcp_servers.<name>]`.
- `enabled` is optional and setting it to `false` disables a server without
  deleting it.
- `bearer_token_env_var`, `env_vars`, and `env_http_headers` support token/env
  reference workflows.
- Codex config override keys can use dot notation such as
  `mcp_servers.context7.enabled=false`.
