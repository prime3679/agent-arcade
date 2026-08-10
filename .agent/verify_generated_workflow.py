#!/usr/bin/env python3
"""Verify the generated-data workflow in an isolated temporary workspace."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PRIVATE_ROUTINE = "fixture-private-routine"
FIXTURE_BRANCH = "codex/signal-room"
REQUIRED_FILES = (
    Path("app/index.html"),
    Path("app/app.js"),
    Path("app/style.css"),
    Path("scripts/build_dist.py"),
    Path("scripts/refresh_deploy.py"),
)
FIXTURE_LATEST = {
    "generated_at": "2026-08-10T08:00:00-04:00",
    "arcade": {"title": "Signal Room · Operations", "location": "local"},
    "hermes": {
        "version": {"ok": True, "version": "1.2.3", "upstream": "abc1234"},
        "gateway": {
            "ok": True,
            "status": "up",
            "reason": "gateway supervision confirmed",
            "checked_at": "2026-08-10T08:00:00-04:00",
            "pid": 76095,
            "command": {"returncode": 0},
        },
        "cron": {
            "ok": True,
            "status": "up",
            "reason": "scheduler activity confirmed",
            "checked_at": "2026-08-10T08:00:00-04:00",
            "active_jobs": 2,
            "next_run": "2026-08-10T09:00:00-04:00",
            "command": {"returncode": 0},
        },
        "cron_list": {
            "ok": True,
            "count": 2,
            "entries": [
                {
                    "id": "deadbeef",
                    "name": PRIVATE_ROUTINE,
                    "state": "active",
                    "schedule": "0 9 * * *",
                    "next_run": "2026-08-10T09:00:00-04:00",
                    "workdir": "/Users/private/medical",
                },
                {
                    "id": "beadfeed",
                    "name": "fixture-household-brief",
                    "state": "active",
                    "schedule": "once",
                    "next_run": "2026-08-10T13:00:00-04:00",
                },
            ],
            "command": {"returncode": 0},
        },
    },
    "repo": {
        "branch": FIXTURE_BRANCH,
        "head": "abc1234",
        "clean": True,
        "changed_files": 0,
        "checked_at": "2026-08-10T08:00:00-04:00",
        "status_lines": ["M app/app.js"],
    },
    "run_history_count": 25,
    "summon": {"telegram": "private free text"},
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(ROOT), help="Repo root to verify.")
    parser.add_argument("--fixture-latest", help="Optional JSON file that overrides the built-in latest fixture.")
    return parser.parse_args(argv)


def require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(message)


def load_json_fixture(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"{label} fixture is missing: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} fixture is malformed: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} fixture must decode to a JSON object")
    return payload


def validate_latest_fixture(payload: dict[str, Any]) -> None:
    for key, expected_type in {"generated_at": str, "hermes": dict, "repo": dict}.items():
        if not isinstance(payload.get(key), expected_type):
            raise SystemExit(f"latest fixture must contain {key!r} as {expected_type.__name__}")
    for key in ("gateway", "cron", "cron_list"):
        if not isinstance(payload["hermes"].get(key), dict):
            raise SystemExit(f"latest fixture must contain hermes.{key} as dict")
    for key in ("gateway", "cron"):
        probe = payload["hermes"][key]
        if probe.get("status") not in {"up", "down", "unverified"}:
            raise SystemExit(f"latest fixture hermes.{key}.status must use the tri-state contract")
        if not isinstance(probe.get("reason"), str) or not isinstance(probe.get("checked_at"), str):
            raise SystemExit(f"latest fixture hermes.{key} must include reason and checked_at")


def load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def exercise_workflow(repo_root: Path, latest_payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    with tempfile.TemporaryDirectory(prefix="signal-room-verify-") as temp_dir:
        temp_root = Path(temp_dir) / "repo"
        temp_root.mkdir()
        for relative_path in REQUIRED_FILES:
            source = repo_root / relative_path
            require_file(source, f"verify_generated_workflow requires {relative_path.as_posix()} in the repo")
            destination = temp_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        data_path = temp_root / "data" / "latest.json"
        data_path.parent.mkdir()
        data_path.write_text(json.dumps(latest_payload, indent=2) + "\n", encoding="utf-8")

        build_dist = load_module("verify_build_dist", temp_root / "scripts" / "build_dist.py")
        refresh_deploy = load_module("verify_refresh_deploy", temp_root / "scripts" / "refresh_deploy.py")
        build_dist.main()
        refresh_deploy.validate_dist()

        dist_latest = load_json_fixture(temp_root / "dist" / "data" / "latest.json", "dist latest")
        shipped_text = [path.read_text(encoding="utf-8") for path in temp_root.joinpath("dist").rglob("*") if path.is_file()]
        return dist_latest, shipped_text


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()
    latest_payload = load_json_fixture(Path(args.fixture_latest).resolve(), "latest") if args.fixture_latest else FIXTURE_LATEST
    validate_latest_fixture(latest_payload)

    previous = sys.dont_write_bytecode
    previous_env = os.environ.get("PYTHONDONTWRITEBYTECODE")
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        dist_latest, shipped_text = exercise_workflow(repo_root, latest_payload)
    finally:
        sys.dont_write_bytecode = previous
        if previous_env is None:
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            os.environ["PYTHONDONTWRITEBYTECODE"] = previous_env

    joined = "\n".join(shipped_text)
    for forbidden in (PRIVATE_ROUTINE, "fixture-household-brief", FIXTURE_BRANCH, "76095", "/Users/private", "abc1234", "private free text"):
        if forbidden in joined:
            raise SystemExit(f"public build exposed forbidden fixture value: {forbidden}")
    if dist_latest.get("visibility") != "public":
        raise SystemExit("dist/data/latest.json must identify public visibility")
    if dist_latest.get("hermes", {}).get("gateway", {}).get("status") != "up":
        raise SystemExit("dist/data/latest.json must preserve verified gateway status")
    if any("name" in entry for entry in dist_latest.get("hermes", {}).get("cron_list", {}).get("entries", [])):
        raise SystemExit("dist/data/latest.json must not expose routine names")
    if "branch" in dist_latest.get("repo", {}):
        raise SystemExit("dist/data/latest.json must not expose the repository branch")

    print("verify_generated_workflow passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
