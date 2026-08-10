# Publishing Signal Room · Operations

The current target remains `arcade.adrianlumley.co`. Domain migration is intentionally out of scope.

Only the sanitized static `dist/` tree may be published. It contains the app, a public-redacted `data/latest.json`, the root redirect, and `CNAME`. It must not contain local run history, summon output, routine names, process IDs, paths, command output, provider/auth detail, git hashes, or private context.

## Local build and privacy validation

```bash
python3 scripts/collect_state.py
python3 scripts/build_dist.py
python3 -c 'import scripts.refresh_deploy as r; r.validate_dist()'
```

## Explicit deployment path

```bash
python3 scripts/refresh_deploy.py
```

That command refreshes local state and the local-only summon artifact, builds and validates `dist/`, commits eligible source changes, and publishes `dist/` to `gh-pages`. It requires `main` and performs external writes. Do not run it for ordinary verification or from a feature branch.

Useful controls:

```bash
python3 scripts/refresh_deploy.py --dry-run
python3 scripts/refresh_deploy.py --skip-main-push
python3 scripts/refresh_deploy.py --skip-gh-pages
```

The public product has no link to the separate Signal Room fiction serial.
