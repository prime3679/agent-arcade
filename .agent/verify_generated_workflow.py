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
REQUIRED_FILES = (
    Path("app/index.html"),
    Path("app/app.js"),
    Path("app/style.css"),
    Path("scripts/build_dist.py"),
    Path("scripts/refresh_deploy.py"),
)
FIXTURE_LATEST = {
    "generated_at": "2026-07-16T00:00:00-04:00",
    "arcade": {
        "location": "local",
        "mode": "static",
    },
    "hermes": {
        "version": {
            "ok": True,
            "version": "1.2.3",
            "build": "fixture-build",
            "upstream": "abc1234",
            "command": {"returncode": 0},
        },
        "gateway": {
            "ok": True,
            "running": True,
            "command": {"returncode": 0},
        },
        "cron": {
            "ok": True,
            "running": True,
            "active_jobs": 2,
            "next_run": "2026-07-16T00:05:00-04:00",
            "command": {"returncode": 0},
        },
        "cron_list": {
            "ok": True,
            "count": 2,
            "entries": [
                {
                    "id": "deadbeef",
                    "state": "active",
                    "schedule": "*/5 * * * *",
                    "next_run": "2026-07-16T00:05:00-04:00",
                    "last_run": "ok",
                },
                {
                    "id": "beadfeed",
                    "state": "paused",
                    "schedule": "0 * * * *",
                    "next_run": "2026-07-16T01:00:00-04:00",
                    "last_run": "skipped",
                },
            ],
            "command": {"returncode": 0},
        },
    },
    "repo": {
        "clean": True,
        "changed_files": 0,
        "staged_files": 0,
        "unstaged_files": 0,
        "untracked_files": 0,
        "status_lines": ["M app/app.js"],
    },
    "agents": [
        {
            "id": "scout",
            "label": "Scout",
            "role": "Sweep",
            "tagline": "Find drift.",
            "cabinet": "radar",
            "accent": "cobalt",
            "order": 1,
            "status": "ready",
            "signal": "Everything is steady.",
            "private_notes": "must not leak",
        }
    ],
}
FIXTURE_SUMMON = {
    "generated_at": "2026-07-16T00:01:00-04:00",
    "source_snapshot": "2026-07-16T00:00:00-04:00",
    "requested": ["scout", "bard", "rogue-persona"],
    "telegram": "Fixture summon output for deterministic verification.",
    "cartridge_count": 3,
    "cartridges": [
        {
            "persona": "scout",
            "label": "Scout",
            "slot": "branch-radar",
            "accent": "cobalt",
            "stamp": "repo sweep",
            "headline": "Sweep for drift.",
            "body": "Everything important is visible.",
            "telegram": "Scout telegram",
            "command": {"returncode": 0},
        },
        {
            "persona": "bard",
            "label": "Bard",
            "slot": "signal-stage",
            "accent": "yellow",
            "stamp": "operator brief",
            "headline": "Sing the state.",
            "body": "Keep the brief concise.",
            "telegram": "Bard telegram",
            "raw": "must not leak",
        },
        {
            "persona": "rogue-persona",
            "label": "Ignored",
            "slot": "shadow",
            "accent": "gray",
            "stamp": "ignore",
            "headline": "Should be dropped.",
            "body": "This persona is not public safe.",
            "telegram": "ignored",
        },
    ],
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(ROOT), help="Repo root to verify.")
    parser.add_argument("--fixture-latest", help="Optional JSON file that overrides the built-in latest fixture.")
    parser.add_argument("--fixture-summon", help="Optional JSON file that overrides the built-in summon fixture.")
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
    required_types = {
        "generated_at": str,
        "arcade": dict,
        "hermes": dict,
        "repo": dict,
        "agents": list,
    }
    for key, expected_type in required_types.items():
        if not isinstance(payload.get(key), expected_type):
            raise SystemExit(f"latest fixture must contain {key!r} as {expected_type.__name__}")


def validate_summon_fixture(payload: dict[str, Any]) -> None:
    required_types = {
        "generated_at": str,
        "source_snapshot": str,
        "requested": list,
        "telegram": str,
        "cartridges": list,
    }
    for key, expected_type in required_types.items():
        if not isinstance(payload.get(key), expected_type):
            raise SystemExit(f"summon fixture must contain {key!r} as {expected_type.__name__}")


def load_module(module_name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def copy_required_tree(repo_root: Path, temp_root: Path) -> None:
    for relative_path in REQUIRED_FILES:
        source = repo_root / relative_path
        require_file(source, f"verify_generated_workflow requires {relative_path.as_posix()} in the repo")
        destination = temp_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def exercise_workflow(
    repo_root: Path,
    latest_payload: dict[str, Any],
    summon_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="agent-arcade-verify-") as temp_dir:
        temp_root = Path(temp_dir) / "repo"
        temp_root.mkdir()
        copy_required_tree(repo_root, temp_root)
        write_json(temp_root / "data" / "latest.json", latest_payload)
        write_json(temp_root / "data" / "summon.json", summon_payload)

        build_dist = load_module("verify_build_dist", temp_root / "scripts" / "build_dist.py")
        refresh_deploy = load_module("verify_refresh_deploy", temp_root / "scripts" / "refresh_deploy.py")

        build_dist.main()
        refresh_deploy.validate_dist()

        dist_latest = load_json_fixture(temp_root / "dist" / "data" / "latest.json", "dist latest")
        dist_summon = load_json_fixture(temp_root / "dist" / "data" / "summon.json", "dist summon")
        return dist_latest, dist_summon


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = Path(args.repo_root).resolve()

    latest_payload = (
        load_json_fixture(Path(args.fixture_latest).resolve(), "latest")
        if args.fixture_latest
        else FIXTURE_LATEST
    )
    summon_payload = (
        load_json_fixture(Path(args.fixture_summon).resolve(), "summon")
        if args.fixture_summon
        else FIXTURE_SUMMON
    )

    validate_latest_fixture(latest_payload)
    validate_summon_fixture(summon_payload)

    previous_dont_write_bytecode = sys.dont_write_bytecode
    previous_env = os.environ.get("PYTHONDONTWRITEBYTECODE")
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        dist_latest, dist_summon = exercise_workflow(repo_root, latest_payload, summon_payload)
    finally:
        sys.dont_write_bytecode = previous_dont_write_bytecode
        if previous_env is None:
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
        else:
            os.environ["PYTHONDONTWRITEBYTECODE"] = previous_env

    if dist_latest.get("repo", {}).get("status_lines") is not None:
        raise SystemExit("dist/data/latest.json must not expose repo.status_lines")
    if dist_latest.get("hermes", {}).get("gateway", {}).get("command") is not None:
        raise SystemExit("dist/data/latest.json must not expose hermes.gateway.command")
    if dist_summon.get("cartridge_count") != len(dist_summon.get("cartridges", [])):
        raise SystemExit("dist/data/summon.json cartridge_count does not match cartridges length")
    if "rogue-persona" in dist_summon.get("requested", []):
        raise SystemExit("dist/data/summon.json must drop unsupported requested personas")
    if any(cartridge.get("persona") == "rogue-persona" for cartridge in dist_summon.get("cartridges", [])):
        raise SystemExit("dist/data/summon.json must drop unsupported cartridges")

    print("verify_generated_workflow passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
