#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LATEST = DATA_DIR / "latest.json"
OUT = DATA_DIR / "summon.json"

PERSONAS = ("gremlin", "archivist", "scout", "bard")
BODY_LIMIT = 280
TELEGRAM_LIMIT = 600

PERSONA_META = {
    "gremlin": {
        "label": "Gremlin",
        "slot": "fault-lab",
        "accent": "orange",
        "stamp": "stress pass",
    },
    "archivist": {
        "label": "Archivist",
        "slot": "memory-vault",
        "accent": "plum",
        "stamp": "snapshot note",
    },
    "scout": {
        "label": "Scout",
        "slot": "branch-radar",
        "accent": "cobalt",
        "stamp": "repo sweep",
    },
    "bard": {
        "label": "Bard",
        "slot": "signal-stage",
        "accent": "yellow",
        "stamp": "operator brief",
    },
}


def safe_text(value: str, limit: int, *, preserve_lines: bool = False) -> str:
    if preserve_lines:
        text = "\n".join(re.sub(r"[^\S\n]+", " ", line).strip() for line in str(value or "").splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
    else:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("`", "'")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def load_latest() -> dict:
    if not LATEST.exists():
        raise SystemExit("data/latest.json missing; run scripts/collect_state.py first")
    return json.loads(LATEST.read_text(encoding="utf-8"))


def pick_personas(argv: list[str]) -> list[str]:
    requested = argv[1:] or ["all"]
    if requested == ["all"]:
        return list(PERSONAS)

    seen: list[str] = []
    for name in requested:
        persona = name.strip().lower()
        if persona not in PERSONAS:
            valid = ", ".join(PERSONAS)
            raise SystemExit(f"unknown persona '{name}'; valid options: all, {valid}")
        if persona not in seen:
            seen.append(persona)
    return seen


def find_agent(payload: dict, agent_id: str) -> dict:
    for agent in payload.get("agents", []):
        if agent.get("id") == agent_id:
            return agent
    return {}


def summarize_repo(repo: dict) -> str:
    changed = repo.get("changed_files", 0) or 0
    staged = repo.get("staged_files", 0) or 0
    untracked = repo.get("untracked_files", 0) or 0
    if repo.get("clean"):
        return "Workspace is clean and quiet."
    return f"Workspace drift is visible: {changed} changed, {staged} staged, {untracked} untracked."


def build_cartridge(persona: str, payload: dict) -> dict:
    hermes = payload.get("hermes", {})
    repo = payload.get("repo", {})
    cron = hermes.get("cron", {})
    cron_list = hermes.get("cron_list", {})
    gateway = hermes.get("gateway", {})
    version = hermes.get("version", {})
    meta = PERSONA_META[persona]
    scout = find_agent(payload, "scout")
    archivist = find_agent(payload, "archivist")

    if persona == "gremlin":
        headline = "Probe the seams without touching config."
        body = (
            f"{summarize_repo(repo)} Gateway is {'up' if gateway.get('running') else 'down'}, "
            f"with {cron_list.get('count', 0)} scheduled routines in the bay. "
            "Focus on awkward edges, surprising combinations, and anything that could jam a local-only flow."
        )
    elif persona == "archivist":
        headline = "Preserve the operator story in clean public-safe notes."
        body = (
            f"Latest snapshot landed at {payload.get('generated_at', 'unknown time')}. "
            f"{archivist.get('signal') or 'Snapshot history is active.'} "
            f"Hermes reports version {version.get('version') or '?'} and {cron_list.get('count', 0)} visible routines."
        )
    elif persona == "scout":
        headline = "Sweep for drift, friction, and next repair targets."
        body = (
            f"{scout.get('signal') or summarize_repo(repo)} "
            f"Repo cleanliness is {'good' if repo.get('clean') else 'not clean'}, "
            f"and the next scheduler tick is {cron.get('next_run') or 'not scheduled'}. "
            "Map the sharpest local risks before they turn into operator confusion."
        )
    else:
        headline = "Turn the cabinet state into a crisp operator briefing."
        body = (
            f"Agent Arcade is running in {payload.get('arcade', {}).get('location', 'local')} mode. "
            f"Gateway is {'online' if gateway.get('running') else 'offline'}, "
            f"cron shows {cron_list.get('count', 0)} routines, and the fleet mood is "
            f"{'steady' if repo.get('clean') else 'restless'}. "
            "Write with signal, compression, and a little cabinet drama."
        )

    body = safe_text(body, BODY_LIMIT)
    telegram = safe_text(
        f"{meta['label']} cartridge\n"
        f"{headline}\n"
        f"{body}",
        TELEGRAM_LIMIT,
        preserve_lines=True,
    )

    return {
        "persona": persona,
        "label": meta["label"],
        "slot": meta["slot"],
        "accent": meta["accent"],
        "stamp": meta["stamp"],
        "headline": headline,
        "body": body,
        "telegram": telegram,
    }


def build_payload(selected: list[str], latest: dict) -> dict:
    cartridges = [build_cartridge(persona, latest) for persona in selected]
    telegram_lines = [
        "Summon Mode",
        f"Snapshot {latest.get('generated_at', 'unknown')}",
        "",
    ]
    for cartridge in cartridges:
        telegram_lines.extend(
            [
                f"[{cartridge['label']}] {cartridge['headline']}",
                cartridge["body"],
                "",
            ]
        )

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_snapshot": latest.get("generated_at"),
        "requested": selected,
        "cartridge_count": len(cartridges),
        "telegram": safe_text(
            "\n".join(telegram_lines).strip(),
            TELEGRAM_LIMIT * max(1, len(cartridges)),
            preserve_lines=True,
        ),
        "cartridges": cartridges,
    }


def main(argv: list[str]) -> int:
    selected = pick_personas(argv)
    latest = load_latest()
    payload = build_payload(selected, latest)
    DATA_DIR.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print()
    print(payload["telegram"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
