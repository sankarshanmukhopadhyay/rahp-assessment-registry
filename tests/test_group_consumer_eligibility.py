import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_group_consumer_eligibility as gate

class ConsumerEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.intent = json.loads((ROOT / "outbox/pending/spec-dependency-2026-11-16.json").read_text())
        self.issues = {}
        for number in gate.NUMBERS:
            self.issues[number] = {
                "number": number, "html_url": gate.PREFIX + str(number),
                "state": "closed" if number in (615,282) else "open",
                "body": (gate.MARKER + "\n" + "\n".join(self.intent["source_finding_ids"])
                         if number == 272 else gate.MARKER if number == 615
                         else "Independent residual"),
                "labels": ([{"name": "dtg-instance"},
                            {"name": "assessment-evidence-complete"}] if number == 272 else [])
            }
        self.combined = SimpleNamespace(
            is_combined=lambda issue: (issue["state"] == "open"
                and gate.GROUP in (issue.get("body") or "")
                and bool({"assessment-required", "judgment-required"} &
                         {x["name"] for x in issue["labels"]})),
            label_names=lambda issue: {x["name"] for x in issue["labels"]})
        self.dpip = SimpleNamespace(
            REQUESTED="assurance:dpip-requested", COMPLETE="assurance:dpip-complete",
            issue_has_label=lambda issue, label: label in {x["name"] for x in issue["labels"]})

    def evaluate(self):
        return gate.evaluate(self.intent, self.issues, self.combined, self.dpip)

    def test_current_source_preserves_all_namespaces_without_auto_dispatch(self):
        output = self.evaluate()
        self.assertEqual(output["state"], "consumer_migration_blocked")
        self.assertFalse(output["combined_review_worker_eligible"])
        self.assertFalse(output["dpip_handoff_eligible"])
        self.assertFalse(output["dpip_lifecycle_issue_eligible"])
        self.assertFalse(output["registry_to_toolkit_issue_number_dispatch_authorized"])
        self.assertFalse(output["registry_case_execution_adapter_qualified"])
        self.assertFalse(output["cutover_authorized"])
        self.assertIsNone(output["assurance_determination"])

    def test_changed_worker_labels_do_not_create_registry_approval(self):
        self.issues[272]["labels"].append({"name": "judgment-required"})
        output = self.evaluate()
        self.assertTrue(output["combined_review_worker_eligible"])
        self.assertFalse(output["registry_to_toolkit_issue_number_dispatch_authorized"])
        self.assertFalse(output["registry_case_execution_adapter_qualified"])
        self.issues[272]["labels"].append({"name": "assurance:dpip-requested"})
        output = self.evaluate()
        self.assertTrue(output["dpip_handoff_eligible"])
        self.assertFalse(output["specialist_return_controller_reconciled"])

    def test_mismatched_and_substituted_issue_ids_fail_closed(self):
        self.issues[272]["number"] = 47
        with self.assertRaisesRegex(gate.ConsumerGateError, "namespace"):
            self.evaluate()
        self.issues[272]["number"] = 272
        self.intent["toolkit_current_issue_url"] = gate.PREFIX + "47"
        with self.assertRaisesRegex(gate.ConsumerGateError, "namespaces"):
            self.evaluate()

    def test_missing_residual_or_invalid_original_marker_fails(self):
        self.issues.pop(837)
        with self.assertRaisesRegex(gate.ConsumerGateError, "incomplete"):
            self.evaluate()
        self.setUp()
        self.issues[615]["body"] = "no historical key"
        with self.assertRaisesRegex(gate.ConsumerGateError, "no longer matches"):
            self.evaluate()

    def test_changed_group_finding_digest_fails(self):
        self.intent["source_finding_ids"] = ["a"*20]
        with self.assertRaisesRegex(gate.ConsumerGateError, "membership"):
            self.evaluate()
        self.setUp()
        self.intent["source_group_sha256"] = "unqualified"
        with self.assertRaisesRegex(gate.ConsumerGateError, "digest"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
