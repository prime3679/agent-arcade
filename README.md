# Signal Room · Operations

Signal Room is a dependency-free, read-only operational report backed by generated JSON snapshots. It is a separate product from the public Signal Room fiction serial and does not link to it.

The page is a mobile-first editorial read: one computed verdict, four sourced signals, the next 24 hours, and a small run-history colophon. It distinguishes verified up, verified down, and unverified; snapshots older than 12 hours cannot make operational claims.

## Data boundary

- `scripts/collect_state.py` runs read-only local Hermes and git commands and writes the full local snapshot to `data/latest.json` plus retained history in `data/runs/`.
- `scripts/build_dist.py` builds the public-safe `dist/` tree. The public JSON omits routine names, process IDs, paths, raw output, provider/auth detail, free-text summons, git hashes, and private operational context.
- `app/` is static HTML, CSS, and JavaScript and reads generated JSON only. A `file://` load uses clearly labeled fictional sample data.
- `scripts/summon.py` remains a local-only briefing artifact. It is not read by the product and is never copied into `dist/`.

No external service is called, no cron job or Hermes configuration is changed, and run history remains capped at 25 snapshots.

## Run locally

```bash
python3 scripts/collect_state.py
python3 scripts/build_dist.py
python3 -m http.server 8000
```

Open `http://localhost:8000/app/` for the local-full view or `http://localhost:8000/dist/app/` for the public-redacted build.

## Verify

```bash
python3 -m unittest discover -s tests
node --test tests/test_app.js
python3 .agent/zero_context_gate.py audit --repo-root .
python3 .agent/zero_context_gate.py verify --repo-root .
```

Publishing remains configured for `arcade.adrianlumley.co`, but verification does not publish. See `PUBLISHING.md` for the explicit deployment path.
