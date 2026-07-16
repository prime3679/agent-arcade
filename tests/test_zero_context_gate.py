from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GATE = ROOT / ".agent" / "zero_context_gate.py"


def run_gate(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(GATE), *args],
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ZeroContextGateTests(unittest.TestCase):
    maxDiff = None

    def test_repo_contract_audit_passes(self) -> None:
        result = run_gate("audit", "--repo-root", str(ROOT))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS audit", result.stdout)

    def test_gate_verify_passes_for_minimal_local_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "docs").mkdir()
            (repo / ".agent").mkdir()
            (repo / "docs" / "guide.md").write_text("hello\n", encoding="utf-8")
            (repo / "check.py").write_text("print('ok')\n", encoding="utf-8")
            contract = {
                "version": 1,
                "repo": "fixture",
                "canonical_doctrine": "docs/guide.md",
                "source_of_truth": ["docs/guide.md", ".agent/contribution-contract.json"],
                "required_files": ["docs/guide.md", "check.py"],
                "boundaries": {
                    "portable_paths": ["docs/", ".agent/"],
                    "protected_paths": ["docs/guide.md"],
                    "forbidden_actions": ["none"],
                },
                "review": {
                    "rules": ["stay local"],
                    "classification": {
                        "one_off_judgment": "taste",
                        "repeatable_defect": "repeatable",
                        "missing_domain_knowledge": "missing",
                        "agent_behavior_failure": "behavior",
                    },
                },
                "escalate_if": ["blocked"],
                "verification": {
                    "commands": [
                        {
                            "id": "check",
                            "cwd": ".",
                            "argv": ["python3", "check.py"],
                        }
                    ]
                },
            }
            (repo / ".agent" / "contribution-contract.json").write_text(
                json.dumps(contract, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_gate("verify", "--repo-root", str(repo))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS verify", result.stdout)
            self.assertIn("command check: ok", result.stdout)

    def test_gate_audit_rejects_forbidden_inline_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "docs").mkdir()
            (repo / ".agent").mkdir()
            (repo / "docs" / "guide.md").write_text("hello\n", encoding="utf-8")
            contract = {
                "version": 1,
                "repo": "fixture",
                "canonical_doctrine": "docs/guide.md",
                "source_of_truth": ["docs/guide.md", ".agent/contribution-contract.json"],
                "required_files": ["docs/guide.md"],
                "boundaries": {
                    "portable_paths": ["docs/", ".agent/"],
                    "protected_paths": ["docs/guide.md"],
                    "forbidden_actions": ["none"],
                },
                "review": {
                    "rules": ["stay local"],
                    "classification": {
                        "one_off_judgment": "taste",
                        "repeatable_defect": "repeatable",
                        "missing_domain_knowledge": "missing",
                        "agent_behavior_failure": "behavior",
                    },
                },
                "escalate_if": ["blocked"],
                "verification": {
                    "commands": [
                        {
                            "id": "bad",
                            "cwd": ".",
                            "argv": ["python3", "-c", "print('nope')"],
                        }
                    ]
                },
            }
            (repo / ".agent" / "contribution-contract.json").write_text(
                json.dumps(contract, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_gate("audit", "--repo-root", str(repo))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("uses inline code execution, which is forbidden", result.stdout)

    def test_workflow_verifier_fails_closed_without_generated_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            shutil.copytree(ROOT / ".agent", repo / ".agent")
            result = subprocess.run(
                ["python3", str(repo / ".agent" / "verify_generated_workflow.py")],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("requires data/latest.json", result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
