# Signal Room · Operations

A local-first, static, read-only operational report. The public build is a redacted version of it. It is a separate product from the retired Signal Room fiction serial.

## Boundaries, with their reasons
- The app reads generated JSON only. That is what keeps it static and safe to publish.
- Collectors may inspect local Hermes and git state with read-only commands. Do not change Hermes config, Hermes state or cron definitions: this repo reports on the system, it does not run it.
- Do not send data off the machine or change auth. The public build is redacted, and nothing else should leave.
- Keep the repo dependency-free. Do not add packages or a package manager; use the Python and Node standard libraries.

## Steps that need no approval
- Running and re-running the tests, `collect_state.py`, `build_dist.py` and both gate commands below.
- Retrying any command in this list that failed or timed out. They are all safe to repeat.
- `python3 scripts/refresh_deploy.py --dry-run`, which publishes nothing.
- Editing app, scripts, tests, fixtures and docs as the task needs, on a branch, then pushing it and opening a pull request.

## Steps that need Adrian's go-ahead, unless the task text gives it
- Publishing: `python3 scripts/refresh_deploy.py` without `--dry-run`, or any other change to `arcade.adrianlumley.co`. It pushes to `main` and `gh-pages`.
- Merging into main.

## When doctrine doesn't cover a case
Take the reading that keeps the static, generated-JSON architecture, say which reading you took in your handoff, and keep going. Stop only when the change cannot be made without breaking a boundary above.

## Verification
- Contract: `.agent/contribution-contract.json`. Doctrine: `docs/zero-context-contribution.md`.
- Before structural work: `python3 .agent/zero_context_gate.py audit --repo-root .`
- Before handoff: `python3 .agent/zero_context_gate.py verify --repo-root .`
- Verify is a local trust check, not a sandbox. It stays deterministic and read-only against the repo and live Hermes state, and it fails closed when fixtures, scripts or assets are missing or malformed.

## Review labels
- `one_off_judgment`: a taste or tradeoff call with no reusable defect.
- `repeatable_defect`: a behavior, contract or verification issue another fresh agent would likely repeat.
- `missing_domain_knowledge`: product or Hermes knowledge that the repo docs don't contain.
- `agent_behavior_failure`: ignored instructions, unsafe actions or skipped verification.
