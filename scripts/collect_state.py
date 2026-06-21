#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "arcade.yaml"
DATA_DIR = ROOT / "data"
RUNS_DIR = DATA_DIR / "runs"
RUN_RETENTION = 25


def read_arcade_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")

    top_level: dict[str, Any] = {}
    agents: list[dict[str, str]] = []
    current_agent: dict[str, str] | None = None
    in_agents = False

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if raw_line.startswith("agents:"):
            in_agents = True
            continue

        if not in_agents:
            key, value = parse_key_value(raw_line.strip(), line_number)
            top_level[key] = value
            continue

        if raw_line.startswith("  - "):
            if current_agent:
                agents.append(current_agent)
            current_agent = {}
            remainder = raw_line[4:].strip()
            if remainder:
                key, value = parse_key_value(remainder, line_number)
                current_agent[key] = value
            continue

        if raw_line.startswith("    ") and current_agent is not None:
            key, value = parse_key_value(raw_line.strip(), line_number)
            current_agent[key] = value
            continue

        raise ValueError(f"Unsupported YAML structure at line {line_number}: {raw_line}")

    if current_agent:
        agents.append(current_agent)

    top_level["agents"] = agents
    return top_level


def parse_key_value(line: str, line_number: int) -> tuple[str, str]:
    if ":" not in line:
        raise ValueError(f"Expected key/value pair at line {line_number}: {line}")
    key, value = line.split(":", 1)
    return key.strip(), strip_quotes(value.strip())


def strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def run_command(args: list[str], cwd: Path | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "command": args,
            "returncode": None,
            "stdout": "",
            "stderr": "command not found",
        }

    return {
        "ok": result.returncode == 0,
        "command": args,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def command_metadata(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": result["ok"],
        "command": result["command"],
        "returncode": result["returncode"],
    }


def parse_hermes_version(result: dict[str, Any]) -> dict[str, Any]:
    first_line = first_non_empty_line(result["stdout"])
    version_match = re.search(r"Hermes Agent v([^\s]+)", first_line or "")
    build_match = re.search(r"\(([^)]+)\)", first_line or "")
    upstream_match = re.search(r"upstream ([0-9a-f]+)", first_line or "")

    return {
        "ok": result["ok"],
        "summary": first_line,
        "version": version_match.group(1) if version_match else None,
        "build": build_match.group(1) if build_match else None,
        "upstream": upstream_match.group(1) if upstream_match else None,
        "command": command_metadata(result),
    }


def parse_gateway_status(result: dict[str, Any]) -> dict[str, Any]:
    text = result["stdout"]
    running = "gateway service is loaded" in text.lower() or "gateway is running" in text.lower()
    pid_match = re.search(r'"PID"\s*=\s*(\d+)|\bPID\b:\s*(\d+)', text)
    heartbeat_match = re.search(r"Ticker heartbeat:\s*(.+)", text)
    profile_lines = re.findall(r"^\s*[✓-]\s+([^\s]+)\s+—\s+PID\s+(\d+)", text, re.MULTILINE)

    return {
        "ok": result["ok"],
        "running": running,
        "pid": int(next(group for group in pid_match.groups() if group)) if pid_match else None,
        "heartbeat": heartbeat_match.group(1).strip() if heartbeat_match else None,
        "other_profiles": [{"name": name, "pid": int(pid)} for name, pid in profile_lines],
        "command": command_metadata(result),
    }


def parse_cron_status(result: dict[str, Any]) -> dict[str, Any]:
    text = result["stdout"]
    lower_text = text.lower()
    running = False
    if "not running" in lower_text:
        running = False
    elif "cron jobs will fire automatically" in lower_text:
        running = True
    elif re.search(r"\bcron\b.*\brunning\b", lower_text):
        running = True
    count_match = re.search(r"(\d+)\s+active job\(s\)", text)
    next_run_match = re.search(r"Next run:\s*(.+)", text)

    return {
        "ok": result["ok"],
        "running": running,
        "active_jobs": int(count_match.group(1)) if count_match else None,
        "next_run": next_run_match.group(1).strip() if next_run_match else None,
        "command": command_metadata(result),
    }


def parse_cron_list(result: dict[str, Any]) -> dict[str, Any]:
    text = result["stdout"]
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in text.splitlines():
        header_match = re.match(r"^\s*([0-9a-f]+)\s+\[(.+)\]\s*$", line)
        if header_match:
            if current:
                entries.append(current)
            current = {"id": header_match.group(1), "state": header_match.group(2)}
            continue

        if current is None:
            continue

        detail_match = re.match(r"^\s+([A-Za-z ]+):\s+(.+)$", line)
        if detail_match:
            key = detail_match.group(1).strip().lower().replace(" ", "_")
            current[key] = detail_match.group(2).strip()

    if current:
        entries.append(current)

    return {
        "ok": result["ok"],
        "count": len(entries),
        "entries": entries,
        "command": command_metadata(result),
    }


def parse_git_status(repo_path: Path) -> dict[str, Any]:
    branch = run_command(["git", "branch", "--show-current"], cwd=repo_path)
    head = run_command(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path)
    status = run_command(["git", "status", "--short"], cwd=repo_path)

    lines = [line for line in status["stdout"].splitlines() if line.strip()]
    counters = Counter()
    for line in lines:
        if len(line) < 2:
            continue
        staged_flag = line[0]
        unstaged_flag = line[1]
        is_untracked = staged_flag == "?" and unstaged_flag == "?"
        if staged_flag != " " and not is_untracked:
            counters["staged"] += 1
        if unstaged_flag != " " and not is_untracked:
            counters["unstaged"] += 1
        if is_untracked:
            counters["untracked"] += 1

    return {
        "branch": branch["stdout"] or None,
        "head": head["stdout"] or None,
        "clean": len(lines) == 0,
        "changed_files": len(lines),
        "staged_files": counters["staged"],
        "unstaged_files": counters["unstaged"],
        "untracked_files": counters["untracked"],
        "status_lines": lines,
        "commands": {
            "branch": command_metadata(branch),
            "head": command_metadata(head),
            "status": command_metadata(status),
        },
    }


def first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def enrich_agents(config_agents: list[dict[str, str]], state: dict[str, Any]) -> list[dict[str, Any]]:
    gateway_running = state["hermes"]["gateway"]["running"]
    cron_running = state["hermes"]["cron"]["running"]
    git_clean = state["repo"]["clean"]
    run_count = state["hermes"]["cron_list"]["count"]

    enriched: list[dict[str, Any]] = []
    for index, agent in enumerate(config_agents):
        live_status = "ready"
        signal = "All systems stable."

        if agent["id"] == "sentinel" and not gateway_running:
            live_status = "warning"
            signal = "Gateway is offline."
        elif agent["id"] == "ticker" and not cron_running:
            live_status = "warning"
            signal = "Scheduler is not running."
        elif agent["id"] == "scout" and not git_clean:
            live_status = "active"
            signal = f"{state['repo']['changed_files']} file(s) changed in this repo."
        elif agent["id"] == "archivist":
            live_status = "active"
            signal = "Writing replayable snapshots to data/runs/."
        elif agent["id"] == "patchbay" and run_count:
            live_status = "active"
            signal = f"{run_count} cron job definitions detected."

        enriched.append(
            {
                **agent,
                "order": index + 1,
                "status": live_status,
                "signal": signal,
            }
        )

    return enriched


def build_payload() -> dict[str, Any]:
    config = read_arcade_config(CONFIG_PATH)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    hermes_version = parse_hermes_version(run_command(["hermes", "version"], cwd=ROOT))
    gateway_status = parse_gateway_status(run_command(["hermes", "gateway", "status"], cwd=ROOT))
    cron_status = parse_cron_status(run_command(["hermes", "cron", "status"], cwd=ROOT))
    cron_list = parse_cron_list(run_command(["hermes", "cron", "list"], cwd=ROOT))
    repo = parse_git_status(ROOT)

    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "arcade": {
            "title": config.get("title", "Agent Arcade"),
            "subtitle": config.get("subtitle", ""),
            "location": config.get("location", "local"),
            "agent_count": len(config.get("agents", [])),
        },
        "hermes": {
            "version": hermes_version,
            "gateway": gateway_status,
            "cron": cron_status,
            "cron_list": cron_list,
        },
        "repo": repo,
        "agents": [],
    }
    payload["agents"] = enrich_agents(config.get("agents", []), payload)
    return payload


def sanitize_persisted_payload(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"raw", "stdout", "stderr"}:
                continue
            cleaned[key] = sanitize_persisted_payload(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_persisted_payload(item) for item in value]
    return value


def write_payload(payload: dict[str, Any]) -> tuple[Path, Path]:
    DATA_DIR.mkdir(exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    latest_path = DATA_DIR / "latest.json"
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")
    run_path = RUNS_DIR / f"{stamp}.json"
    sanitized_payload = sanitize_persisted_payload(payload)
    body = json.dumps(sanitized_payload, indent=2) + "\n"

    latest_path.write_text(body, encoding="utf-8")
    run_path.write_text(body, encoding="utf-8")
    scrub_legacy_snapshots()
    prune_run_history()
    return latest_path, run_path


def prune_run_history(limit: int = RUN_RETENTION) -> None:
    run_files = sorted(RUNS_DIR.glob("*.json"))
    for stale_path in run_files[:-limit]:
        stale_path.unlink(missing_ok=True)


def scrub_legacy_snapshots() -> None:
    snapshot_paths = [DATA_DIR / "latest.json", *sorted(RUNS_DIR.glob("*.json"))]
    for snapshot_path in snapshot_paths:
        if not snapshot_path.exists():
            continue
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
        sanitized = sanitize_persisted_payload(payload)
        snapshot_path.write_text(json.dumps(sanitized, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    try:
        payload = build_payload()
        latest_path, run_path = write_payload(payload)
    except Exception as exc:
        print(f"collect_state failed: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {latest_path.relative_to(ROOT)}")
    print(f"Wrote {run_path.relative_to(ROOT)}")
    print(
        "Snapshot: "
        f"Hermes {payload['hermes']['version']['version'] or 'unknown'} | "
        f"gateway={'up' if payload['hermes']['gateway']['running'] else 'down'} | "
        f"cron_jobs={payload['hermes']['cron_list']['count']} | "
        f"git_clean={payload['repo']['clean']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
