#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
APP = ROOT / "app"
DATA = ROOT / "data" / "latest.json"
CNAME = "arcade.adrianlumley.co"
VALID_STATUSES = {"up", "down", "unverified"}
SAFE_ENTRY_STATES = {"active", "paused", "disabled", "unknown"}


def safe_datetime(value: Any) -> str | None:
    text = str(value or "")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})", text):
        return text
    return None


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def public_probe(probe: dict[str, Any], label: str) -> dict[str, Any]:
    status = probe.get("status")
    if status not in VALID_STATUSES:
        status = "up" if probe.get("running") is True else "unverified"
    reasons = {
        "up": f"{label} activity confirmed",
        "down": f"{label} explicitly reported unavailable",
        "unverified": f"{label} could not be verified",
    }
    return {
        "status": status,
        "reason": reasons[status],
        "checked_at": safe_datetime(probe.get("checked_at")),
    }


def safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    hermes = payload.get("hermes", {})
    repo = payload.get("repo", {})
    cron = hermes.get("cron", {})
    cron_list = hermes.get("cron_list", {})
    entries = cron_list.get("entries", []) or []
    safe_entries = [
        {
            "state": entry.get("state") if entry.get("state") in SAFE_ENTRY_STATES else "unknown",
            "next_run": safe_datetime(entry.get("next_run")),
            "schedule": "once" if "once" in str(entry.get("schedule", "")).lower() else None,
        }
        for entry in entries[:24]
    ]

    gateway = public_probe(hermes.get("gateway", {}), "gateway")
    scheduler = public_probe(cron, "scheduler")
    scheduler.update({
        "active_jobs": cron.get("active_jobs"),
        "next_run": safe_datetime(cron.get("next_run")),
    })

    return {
        "generated_at": payload.get("generated_at"),
        "visibility": "public",
        "hermes": {
            "gateway": gateway,
            "cron": scheduler,
            "cron_list": {
                "count": cron_list.get("count"),
                "entries": safe_entries,
            },
        },
        "repo": {
            "clean": repo.get("clean"),
            "changed_files": repo.get("changed_files"),
            "checked_at": repo.get("checked_at") or payload.get("generated_at"),
        },
        "run_history_count": payload.get("run_history_count"),
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
    public_data = json.dumps(safe_payload(payload), indent=2) + "\n"
    (DIST / "data" / "latest.json").write_text(public_data, encoding="utf-8")

    (DIST / "index.html").write_text("""<!doctype html>
<html lang=\"en\">
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Signal Room · Operations</title>
<meta http-equiv=\"refresh\" content=\"0; url=./app/\">
<link rel=\"canonical\" href=\"./app/\">
<a href=\"./app/\">Open Signal Room · Operations</a>
</html>
""", encoding="utf-8")
    (DIST / "CNAME").write_text(f"{CNAME}\n", encoding="utf-8")

    print(f"Built {DIST}")
    print("Included: app/, data/latest.json, index.html, CNAME")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
