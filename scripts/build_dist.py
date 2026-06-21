#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP = ROOT / "app"
DATA = ROOT / "data" / "latest.json"

SAFE_AGENT_FIELDS = {
    "id", "label", "role", "tagline", "cabinet", "accent", "order", "status", "signal"
}


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def safe_payload(payload: dict) -> dict:
    hermes = payload.get("hermes", {})
    repo = payload.get("repo", {})
    cron = hermes.get("cron", {})
    cron_list = hermes.get("cron_list", {})
    entries = cron_list.get("entries", []) or []

    safe_entries = []
    for i, entry in enumerate(entries[:12], start=1):
        safe_entries.append({
            "id": f"routine-{i:02d}",
            "state": entry.get("state", "active"),
            "name": f"Routine {i:02d}",
            "schedule": entry.get("schedule", "configured"),
            "next_run": entry.get("next_run", "scheduled"),
            "last_run": "ok" if "ok" in str(entry.get("last_run", "")).lower() else "unknown",
        })

    return {
        "generated_at": payload.get("generated_at"),
        "arcade": payload.get("arcade", {}),
        "hermes": {
            "version": {
                "ok": hermes.get("version", {}).get("ok"),
                "version": hermes.get("version", {}).get("version"),
                "build": hermes.get("version", {}).get("build"),
                "upstream": hermes.get("version", {}).get("upstream"),
            },
            "gateway": {
                "ok": hermes.get("gateway", {}).get("ok"),
                "running": hermes.get("gateway", {}).get("running"),
            },
            "cron": {
                "ok": cron.get("ok"),
                "running": cron.get("running"),
                "active_jobs": cron.get("active_jobs"),
                "next_run": cron.get("next_run"),
            },
            "cron_list": {
                "ok": cron_list.get("ok"),
                "count": cron_list.get("count"),
                "entries": safe_entries,
            },
        },
        "repo": {
            "clean": repo.get("clean"),
            "changed_files": repo.get("changed_files"),
            "staged_files": repo.get("staged_files"),
            "unstaged_files": repo.get("unstaged_files"),
            "untracked_files": repo.get("untracked_files"),
        },
        "agents": [
            {k: v for k, v in agent.items() if k in SAFE_AGENT_FIELDS}
            for agent in payload.get("agents", [])
        ],
    }


def main() -> int:
    if not DATA.exists():
        raise SystemExit("data/latest.json missing; run scripts/collect_state.py first")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    copy_tree(APP, DIST / "app")
    (DIST / "data").mkdir()

    payload = json.loads(DATA.read_text(encoding="utf-8"))
    (DIST / "data" / "latest.json").write_text(json.dumps(safe_payload(payload), indent=2) + "\n", encoding="utf-8")

    # Make root URL work.
    root_index = DIST / "index.html"
    root_index.write_text("""<!doctype html>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Agent Arcade</title>
<meta http-equiv=\"refresh\" content=\"0; url=/app/\">
<link rel=\"canonical\" href=\"/app/\">
<a href=\"/app/\">Open Agent Arcade</a>
""", encoding="utf-8")

    print(f"Built {DIST}")
    print("Included: app/, data/latest.json, index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
