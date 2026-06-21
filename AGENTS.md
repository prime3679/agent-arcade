# Agent Arcade

Rogue is the product/control plane. Codex is the primary builder. Claude Code is the second-engineer/deep reviewer. Keep v1 local, static, and safe.

Rules:
- No external sends or auth changes.
- No Hermes config mutations.
- No cron creation in v1.
- Static app reads generated JSON only.
- Scripts may inspect local Hermes status using read-only shell commands.
