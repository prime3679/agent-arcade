# Zero-Context Contribution Standard

Use this repo as a local-first static operational report with a public-redacted build.

Source of truth:
- `AGENTS.md` for control-plane rules and escalation.
- `.agent/contribution-contract.json` for required files and verification commands.
- `README.md` for quick discovery.
- `PUBLISHING.md` only when reviewing publish mechanics. Do not treat it as the default verify path.

Operating model:
- The UI is static and reads generated JSON only.
- `scripts/collect_state.py` may inspect local Hermes and git state with read-only commands.
- `scripts/summon.py` derives local-only briefings from `data/latest.json`; the app and public build do not consume them.
- `scripts/build_dist.py` produces the sanitized static bundle in `dist/`.
- New probes use `{status: up|down|unverified, reason, checked_at}`. Unknown, failed, or missing command results are unverified; only explicit negative output is down.
- Public artifacts contain schedule times and counts, never routine names or free-text summons.
- Any collector or summon schema change must update the deterministic fixtures and verifier tests in the same contribution.

Trust boundary:
- Verify is honest about local trust. It is not a sandbox, and it must not inspect live Hermes state or mutate tracked or untracked repo files.
- Fail closed when deterministic verifier fixtures or copied workflow inputs are missing or malformed.
- This repo reports on Hermes; it does not run it. So it never creates cron jobs, changes Hermes config or state, sends data externally, starts persistent servers, exposes the network, or reads secrets.

Fresh-agent contribution flow:
1. Read `AGENTS.md`, this document, and `README.md`.
2. Run `python3 .agent/zero_context_gate.py audit --repo-root .`.
3. Make the change on a branch. Product UI and data are in scope when the task asks for them; Hermes config/state, auth, services and new dependencies stay out of scope.
4. Run `python3 .agent/zero_context_gate.py verify --repo-root .`.
5. Run any requested deterministic checks, then push the branch and open a pull request. Retrying a failed or timed-out check needs no approval.

Review standard:
- Report `repeatable_defect` first when behavior or verification can fail again for a fresh agent.
- Use `missing_domain_knowledge` when repo-local doctrine is insufficient.
- Use `agent_behavior_failure` when instructions or safety boundaries were missed.
- Keep `one_off_judgment` rare and clearly non-blocking.
