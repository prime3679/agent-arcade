# Agent Arcade v1

Agent Arcade is a dependency-free local static dashboard backed by generated JSON snapshots.

## Files

- `arcade.yaml`: cabinet roster for the dashboard
- `scripts/collect_state.py`: collects local Hermes and repo state using read-only commands
- `data/latest.json`: most recent generated snapshot
- `data/runs/*.json`: timestamped snapshot history
- `app/`: static HTML, CSS, and JavaScript UI

## Run

Generate a fresh snapshot:

```bash
python3 scripts/collect_state.py
```

Serve the project locally so the app can fetch `data/latest.json`:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/app/
```

Refresh the snapshot set, rebuild the public-safe `dist/` bundle, validate the leak check, and deploy:

```bash
python3 scripts/refresh_deploy.py
```

Limit the summon step to specific personas:

```bash
python3 scripts/refresh_deploy.py scout bard
```

Verify the full local refresh/build/validation flow without committing or pushing:

```bash
python3 scripts/refresh_deploy.py --dry-run
```

If you open `app/index.html` directly via `file://`, the dashboard will fall back to embedded sample data instead of failing.

## Notes

- The collector uses read-only local commands only: `hermes version`, `hermes gateway status`, `hermes cron status`, `hermes cron list`, and read-only `git` commands for this repo.
- No external services are called.
- No cron jobs are created or modified.
- No Hermes configuration is changed.
- `scripts/refresh_deploy.py` runs `collect_state.py`, `summon.py`, `build_dist.py`, enforces `dist/CNAME` as `arcade.adrianlumley.co`, validates a dist leak check, publishes `dist/` to `gh-pages`, pushes `main` changes if present, and prints the public URL.
- Generated snapshots under `data/` and the built `dist/` directory are local-only runtime artifacts and should not be committed, aside from an optional small sample file if you choose to add one later.
