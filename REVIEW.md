# Review Standard

Use zero-context review labels:
- `repeatable_defect`: likely to recur for another fresh agent. Treat as the default blocking class.
- `missing_domain_knowledge`: repo-local doctrine is insufficient to decide safely.
- `agent_behavior_failure`: instructions, verification, or safety posture were missed.
- `one_off_judgment`: non-reusable preference call. Keep this non-blocking unless the user asks for taste arbitration.

Minimum review bar:
- Check the touched change against `AGENTS.md` and `docs/zero-context-contribution.md`.
- Require `python3 .agent/zero_context_gate.py audit --repo-root .`.
- Require `python3 .agent/zero_context_gate.py verify --repo-root .` before handoff.
