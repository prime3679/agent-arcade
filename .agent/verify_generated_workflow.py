#!/usr/bin/env python3
"""Verify the local generated-data workflow without deploy side effects."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LATEST = ROOT / "data" / "latest.json"
SUMMON = ROOT / "data" / "summon.json"
DIST_LATEST = ROOT / "dist" / "data" / "latest.json"
DIST_SUMMON = ROOT / "dist" / "data" / "summon.json"


def require_file(path: Path, message: str) -> None:
    if not path.is_file():
        raise SystemExit(message)


def main() -> int:
    require_file(LATEST, "verify_generated_workflow requires data/latest.json; run scripts/collect_state.py first")
    require_file(SUMMON, "verify_generated_workflow requires data/summon.json; run scripts/summon.py first")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_dist  # noqa: PLC0415
    import refresh_deploy  # noqa: PLC0415

    build_dist.main()
    refresh_deploy.ensure_cname()
    refresh_deploy.validate_dist()

    latest_payload = json.loads(DIST_LATEST.read_text(encoding="utf-8"))
    summon_payload = json.loads(DIST_SUMMON.read_text(encoding="utf-8"))

    if latest_payload.get("repo", {}).get("status_lines") is not None:
        raise SystemExit("dist/data/latest.json must not expose repo.status_lines")
    if latest_payload.get("hermes", {}).get("gateway", {}).get("command") is not None:
        raise SystemExit("dist/data/latest.json must not expose hermes.gateway.command")
    if summon_payload.get("cartridge_count") != len(summon_payload.get("cartridges", [])):
        raise SystemExit("dist/data/summon.json cartridge_count does not match cartridges length")

    print("verify_generated_workflow passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
