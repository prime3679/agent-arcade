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

1. Create a sanitized build directory, e.g. `dist/`.
2. Copy app files into `dist/`.
3. Generate `dist/data/latest.json` from the local snapshot with private fields removed or renamed.
4. Deploy `dist/` to Cloudflare Pages.
5. Point `arcade.adrian` at the Pages project.
6. Add access control if the surface becomes more than public-safe status art.

## Domain note

`arcade.adrian` may not be a resolvable public DNS name unless Adrian owns or controls that zone/TLD locally. If not, use one of:
- `arcade.adrianlumley.co`
- `agent-arcade.adrianlumley.co`
- a Cloudflare Pages preview URL first

## Process rule

Claude Code owns visual/product design for Agent Arcade. Codex should implement deployment/build mechanics only after Rogue and Adrian select the design direction.
