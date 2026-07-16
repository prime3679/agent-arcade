# Zero-Context Contribution Standard

Use this repo as a local-only static cabinet.

Source of truth:
- `AGENTS.md` for control-plane rules and escalation.
- `.agent/contribution-contract.json` for required files and verification commands.
- `README.md` for quick discovery.
- `PUBLISHING.md` only when reviewing publish mechanics. Do not treat it as the default verify path.

Operating model:
- The UI is static and reads generated JSON only.
- `scripts/collect_state.py` may inspect local Hermes and git state with read-only commands.
- `scripts/summon.py` derives briefings from `data/latest.json`.
- `scripts/build_dist.py` produces the sanitized static bundle in `dist/`.
- Any collector or summon schema change must update the deterministic fixtures and verifier tests in the same contribution.

Trust boundary:
- Verify is honest about local trust. It is not a sandbox, and it must not inspect live Hermes state or mutate tracked or untracked repo files.
- Fail closed when deterministic verifier fixtures or copied workflow inputs are missing or malformed.
- Never create cron jobs, mutate Hermes config/state, send externally, start persistent servers, expose the network, or read secrets.

Fresh-agent contribution flow:
1. Read `AGENTS.md`, this document, and `README.md`.
2. Run `python3 .agent/zero_context_gate.py audit --repo-root .`.
3. Make the change without touching product UI/data, dependencies, lockfiles, Hermes config/state, auth, or services unless the task explicitly requires it and the rules allow it.
4. Run `python3 .agent/zero_context_gate.py verify --repo-root .`.
5. Run any requested deterministic checks plus repo hygiene checks before commit.

Review standard:
- Report `repeatable_defect` first when behavior or verification can fail again for a fresh agent.
- Use `missing_domain_knowledge` when repo-local doctrine is insufficient.
- Use `agent_behavior_failure` when instructions or safety boundaries were missed.
- Keep `one_off_judgment` rare and clearly non-blocking.
