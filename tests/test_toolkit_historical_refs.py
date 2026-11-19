import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "scripts/audit_toolkit_historical_refs.py"
SPEC = importlib.util.spec_from_file_location("historical_ref_audit", MODULE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
REVISION = "a" * 40


class HistoricalRefAuditTests(unittest.TestCase):
    def test_unguarded_workflow_is_source_exposure(self):
        def fake_git(_repo, op, *args):
            if op == "ls-tree":
                return audit.WORKFLOW
            if args[-1].endswith(audit.WORKFLOW):
                return "on:\\n  workflow_dispatch:\\npermissions:\\n  issues: write\\n"
            return "def publish(): pass"
        with patch.object(audit, "git", side_effect=fake_git):
            result = audit.audit(Path("."), [("legacy", REVISION)])
        self.assertEqual(result["unfenced_source_refs"], ["legacy"])
        self.assertFalse(result["cutover_authorized"])

    def test_guard_does_not_certify_exclusivity(self):
        def fake_git(_repo, op, *args):
            if op == "ls-tree":
                return audit.WORKFLOW
            if args[-1].endswith(audit.WORKFLOW):
                return "on:\\n  workflow_dispatch:\\npermissions:\\n  issues: write\\n"
            return "TRANSFER_LEDGER = 1\\ndef enforce_live_transfer_boundary(): pass"
        with patch.object(audit, "git", side_effect=fake_git):
            result = audit.audit(Path("."), [("guarded", REVISION)])
        self.assertEqual(result["unfenced_source_refs"], [])
        self.assertFalse(result["server_enforced_exclusion_verified"])
        self.assertFalse(result["cutover_authorized"])

    def test_retired_default_branch_path_is_not_a_fake_source_failure(self):
        def fake_git(_repo, op, *args):
            self.assertEqual(op, "ls-tree")
            return ""
        with patch.object(audit, "git", side_effect=fake_git):
            report = audit.audit(Path("."), [("main", REVISION)])
        self.assertEqual(report["unfenced_source_refs"], [])
        self.assertFalse(report["refs"][0]["historical_workflow_present"])
        self.assertFalse(report["server_enforced_exclusion_verified"])
        self.assertFalse(report["cutover_authorized"])

    def test_missing_history_refuses_completion(self):
        with self.assertRaisesRegex(ValueError, "empty branch"):
            audit.audit(Path("."), [])

    def test_missing_git_object_refuses_completion(self):
        with patch.object(audit, "git", side_effect=subprocess.CalledProcessError(1, ["git", "show"])):
            with self.assertRaises(subprocess.CalledProcessError):
                audit.audit(Path("."), [("missing", REVISION)])

    def test_unpinned_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned commit"):
            audit.inspect_ref(Path("."), "legacy", "main")

    def test_branch_inventory_requires_valid_ref(self):
        with patch.object(audit, "git", return_value="refs/remotes/origin/old invalid\n"):
            with self.assertRaisesRegex(ValueError, "invalid remote"):
                audit.remote_refs(Path("."))


if __name__ == "__main__":
    unittest.main()
