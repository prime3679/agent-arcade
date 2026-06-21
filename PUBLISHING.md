# Publishing plan for arcade.adrian

Goal: publish Agent Arcade as a private/public-safe static link at `arcade.adrian` or the final domain Adrian chooses.

## Safety posture

Publish only sanitized static assets:
- `app/`
- a public-safe `data/latest.json` export
- optional PNG previews

Do not publish:
- raw command stdout/stderr
- local home paths
- full cron workdirs
- auth/provider details
- family/medical-sensitive labels unless Adrian explicitly approves
- `.git/`, `data/runs/`, `__pycache__/`, local logs

## Recommended deploy path

One-command path:

```bash
python3 scripts/refresh_deploy.py
```

What it does:
- runs `scripts/collect_state.py`
- runs `scripts/summon.py` with all personas by default, or only the personas passed on the command line
- runs `scripts/build_dist.py`
- ensures `dist/CNAME` contains `arcade.adrianlumley.co`
- validates the built `dist/` tree for common leaks before publish
- commits and pushes `main` changes if there are any non-generated repo changes
- publishes `dist/` to the `gh-pages` branch
- prints the public URL: `http://arcade.adrianlumley.co/` until GitHub finishes HTTPS certificate provisioning

Useful variants:

```bash
python3 scripts/refresh_deploy.py scout bard
python3 scripts/refresh_deploy.py --dry-run
python3 scripts/refresh_deploy.py --skip-main-push
python3 scripts/refresh_deploy.py --skip-gh-pages
```

`--dry-run` is the local verification path: it refreshes state, rebuilds `dist/`, enforces the CNAME, and runs the leak check without committing or pushing.

## Domain note

`arcade.adrian` may not be a resolvable public DNS name unless Adrian owns or controls that zone/TLD locally. If not, use one of:
- `arcade.adrianlumley.co`
- `agent-arcade.adrianlumley.co`
- a Cloudflare Pages preview URL first

## Process rule

Claude Code owns visual/product design for Agent Arcade. Codex should implement deployment/build mechanics only after Rogue and Adrian select the design direction.
