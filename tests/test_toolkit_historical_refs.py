import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
MODULE = Path(__file__).resolve().parents[1] / "scripts/audit_toolkit_historical_refs.py"
SPEC = importlib.util.spec_from_file_location("historical_ref_audit", MODULE)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)
REVISION = "a" * 40


class HistoricalRefAuditTests(unittest.TestCase):
    def test_all_current_and_retired_writers_are_in_inventory(self):
        from importlib.util import spec_from_file_location, module_from_spec
        module = Path(__file__).resolve().parents[1] / "scripts/audit_toolkit_issue_writers.py"
        spec = spec_from_file_location("writer_inventory", module)
        inventory = module_from_spec(spec)
        spec.loader.exec_module(inventory)
        expected = {".github/workflows/" + k for k in inventory.EXPECTED}
        expected |= {
            ".github/workflows/dtg-portfolio-materiality-handoff.yml",
            ".github/workflows/instance-watch.yml",
        }
        self.assertEqual(set(audit.WORKFLOWS), expected)

    def test_any_manual_issue_write_is_exposure_even_with_source_guard(self):
        observed = []
        workflow = audit.WORKFLOWS[0]

        def fake_git(_repo, op, *args):
            observed.append((op, args))
            if op == "ls-tree":
                path = args[-1]
                return path if path in (workflow, audit.PUBLISHER) else ""
            if op == "show" and args[-1].endswith(workflow):
                return "on:\n  workflow_dispatch:\npermissions:\n  issues: write\nrun: " + audit.PUBLISHER
            if op == "show" and args[-1].endswith(audit.PUBLISHER):
                return "TRANSFER_LEDGER=1\ndef enforce_live_transfer_boundary(): pass"
            raise AssertionError((op, args))

        with patch.object(audit, "git", side_effect=fake_git):
            result = audit.audit(Path("."), [("tag:v1", REVISION)])
        self.assertEqual(result["unfenced_source_refs"], ["tag:v1"])
        self.assertEqual(result["refs"][0]["potentially_writable_workflows"], [workflow])
        self.assertTrue(result["refs"][0]["workflows"][0]["live_transfer_guard_present"])
        self.assertFalse(result["server_enforced_exclusion_verified"])
        self.assertFalse(result["cutover_authorized"])

    def test_nonmanual_writing_workflow_not_claimed_as_dispatch_surface(self):
        workflow = audit.WORKFLOWS[0]
        def fake_git(_repo, op, *args):
            if op == "ls-tree":
                return args[-1] if args[-1] == workflow else ""
            if op == "show":
                return "on:\n  push:\npermissions:\n  issues: write\n"
            raise AssertionError(op)
        with patch.object(audit, "git", side_effect=fake_git):
            result = audit.audit(Path("."), [("branch:main", REVISION)])
        self.assertEqual(result["unfenced_source_refs"], [])
        self.assertFalse(result["server_enforced_exclusion_verified"])
        self.assertFalse(result["cutover_authorized"])

    def test_absent_workflows_are_not_fake_exposure(self):
        with patch.object(audit, "git", return_value=""):
            result = audit.audit(Path("."), [("branch:main", REVISION)])
        self.assertEqual(result["unfenced_source_refs"], [])
        self.assertEqual(result["refs"][0]["workflows"], [])
        self.assertFalse(result["server_enforced_exclusion_verified"])

    def test_malformed_source_tree_or_missing_publisher_fails_closed(self):
        workflow = audit.WORKFLOWS[0]
        def fake_git(_repo, op, *args):
            if op == "ls-tree":
                if args[-1] == workflow:
                    return workflow
                return ""
            if op == "show":
                return "on:\n  workflow_dispatch:\npermissions:\n  issues: write\nrun: " + audit.PUBLISHER
            raise AssertionError(op)
        with patch.object(audit, "git", side_effect=fake_git):
            with self.assertRaisesRegex(ValueError, "publisher.*missing"):
                audit.audit(Path("."), [("branch:legacy", REVISION)])

    def test_ref_inventory_requires_main_and_valid_refs(self):
        with patch.object(audit, "git", return_value="refs/remotes/origin/old invalid\n"):
            with self.assertRaisesRegex(ValueError, "invalid remote"):
                audit.remote_refs(Path("."))
        with patch.object(audit, "git", return_value="refs/remotes/origin/old " + REVISION + "\n"):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                audit.remote_refs(Path("."))

    def test_annotated_tag_commit_is_resolved_and_distinct(self):
        def fake_git(_repo, op, *args):
            if op == "for-each-ref":
                return ("refs/remotes/origin/main " + REVISION + "\n"
                        + "refs/tags/v1 " + "b" * 40 + "\n")
            if op == "rev-parse":
                self.assertEqual(args[-1], "refs/tags/v1^{commit}")
                return "c" * 40 + "\n"
            raise AssertionError(op)
        with patch.object(audit, "git", side_effect=fake_git):
            result = audit.remote_refs(Path("."))
        self.assertEqual(result, [
            ("branch:main", REVISION), ("tag:v1", "c" * 40),
        ])

    def test_missing_ref_is_fatal(self):
        with patch.object(audit, "git", side_effect=subprocess.CalledProcessError(1, ["git", "show"])):
            with self.assertRaises(subprocess.CalledProcessError):
                audit.audit(Path("."), [("branch:missing", REVISION)])

    def test_unpinned_commit_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned commit"):
            audit.inspect_ref(Path("."), "branch:legacy", "main")

    def test_empty_inventory_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "empty branch"):
            audit.audit(Path("."), [])


if __name__ == "__main__":
    unittest.main()
