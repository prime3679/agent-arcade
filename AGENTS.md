# Agent Arcade

Rogue is the product/control plane. Codex is the primary builder. Claude Code is the second-engineer/deep reviewer. Keep v1 local, static, and safe.

Rules:
- No external sends or auth changes.
- No Hermes config mutations.
- No cron creation in v1.
- Static app reads generated JSON only.
- Scripts may inspect local Hermes status using read-only shell commands.

Precedence:
- System, developer, and user instructions override this file.
- When instructions conflict, preserve the local-only static architecture and escalate instead of guessing.

Verification:
- The zero-context contract lives at `.agent/contribution-contract.json`.
- Canonical contribution doctrine lives at `docs/zero-context-contribution.md`.
- Run `python3 .agent/zero_context_gate.py audit --repo-root .` before structural work.
- Run `python3 .agent/zero_context_gate.py verify --repo-root .` before handoff.
- Verify is a local trust check, not a sandbox. It must stay deterministic and read-only with respect to the repo and live Hermes state, and it must fail closed when required verifier fixtures, scripts, or assets are missing or malformed.

Review Classification:
- `one_off_judgment`: acceptable taste or tradeoff disagreement with no reusable defect.
- `repeatable_defect`: behavior, contract, or verification issue another fresh agent would likely repeat.
- `missing_domain_knowledge`: blocked on product or Hermes knowledge not recoverable from repo-local doctrine.
- `agent_behavior_failure`: ignored instructions, unsafe actions, or missing verification discipline.

Escalation:
- Escalate if verification would need live Hermes mutation, installs, secrets, auth changes, services, or network exposure.
- Escalate if the local-only/generated-JSON architecture conflicts with a requested change or with the shared gate.
