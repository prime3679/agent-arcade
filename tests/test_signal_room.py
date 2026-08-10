from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = load_module("signal_room_collect", ROOT / "scripts" / "collect_state.py")
build = load_module("signal_room_build", ROOT / "scripts" / "build_dist.py")


def command(stdout: str, *, ok: bool = True, returncode: int | None = 0):
    return {"ok": ok, "command": ["hermes"], "returncode": returncode, "stdout": stdout, "stderr": ""}


class ProbeParsingTests(unittest.TestCase):
    def test_current_launchd_wording_is_up(self) -> None:
        probe = collect.parse_gateway_status(
            command("Gateway is supervised by launchd (PID 76095)"),
            "2026-08-10T08:00:00-04:00",
        )
        self.assertEqual(probe["status"], "up")
        self.assertEqual(probe["reason"], "gateway supervision confirmed")
        self.assertEqual(probe["checked_at"], "2026-08-10T08:00:00-04:00")

    def test_unrecognized_gateway_output_is_unverified(self) -> None:
        probe = collect.parse_gateway_status(command("Gateway state: mysterious"))
        self.assertEqual(probe["status"], "unverified")
        self.assertIn("not recognized", probe["reason"])

    def test_nonzero_gateway_output_is_unverified_even_if_negative(self) -> None:
        probe = collect.parse_gateway_status(command("Gateway is not running", ok=False, returncode=1))
        self.assertEqual(probe["status"], "unverified")

    def test_only_explicit_gateway_negative_is_down(self) -> None:
        probe = collect.parse_gateway_status(command("Gateway is not running"))
        self.assertEqual(probe["status"], "down")

    def test_missing_gateway_command_is_unverified(self) -> None:
        probe = collect.parse_gateway_status(command("", ok=False, returncode=None))
        self.assertEqual(probe["status"], "unverified")
        self.assertEqual(probe["reason"], "hermes command not found")

    def test_scheduler_uses_the_same_tri_state_contract(self) -> None:
        up = collect.parse_cron_status(command("Cron jobs will fire automatically\n2 active job(s)"))
        down = collect.parse_cron_status(command("Cron is not running"))
        unknown = collect.parse_cron_status(command("Scheduler response changed"))
        self.assertEqual((up["status"], down["status"], unknown["status"]), ("up", "down", "unverified"))

    def test_run_history_retention_remains_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original = collect.RUNS_DIR
            try:
                collect.RUNS_DIR = Path(temp_dir)
                for index in range(30):
                    (collect.RUNS_DIR / f"{index:02d}.json").write_text("{}\n", encoding="utf-8")
                collect.prune_run_history(25)
                self.assertEqual(len(list(collect.RUNS_DIR.glob("*.json"))), 25)
            finally:
                collect.RUNS_DIR = original

    def test_public_payload_removes_all_private_entry_fields(self) -> None:
        payload = {
            "generated_at": "2026-08-10T08:00:00-04:00",
            "hermes": {
                "gateway": {"status": "up", "reason": "/Users/private", "checked_at": "2026-08-10T08:00:00-04:00", "pid": 12345},
                "cron": {"status": "up", "reason": "provider auth detail", "checked_at": "2026-08-10T08:00:00-04:00"},
                "cron_list": {"count": 1, "entries": [{"name": "rogue-pregnancy-weekly", "id": "deadbeef", "workdir": "/Users/private", "next_run": "raw output"}]},
            },
            "repo": {"head": "abc1234", "clean": True, "changed_files": 0},
        }
        public = build.safe_payload(payload)
        rendered = str(public)
        for secret in ("rogue-pregnancy-weekly", "/Users/private", "12345", "deadbeef", "abc1234", "provider auth detail", "raw output"):
            self.assertNotIn(secret, rendered)
        self.assertEqual(public["hermes"]["gateway"]["status"], "up")
        self.assertEqual(public["hermes"]["cron_list"]["entries"][0]["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
