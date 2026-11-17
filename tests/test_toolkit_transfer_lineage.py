import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_toolkit_transfer_lineage as audit


def inputs():
    ids = ("a" * 20, "b" * 20)
    repo = "OpenVTC/verifiable-trust-infrastructure"
    findings = [{
        "finding_id": fid, "repository": repo,
        "evidence_urls": ["https://github.com/" + repo + "/commit/" + "c" * 40],
        "state": "open", "review_status": "unreviewed",
        "materiality": "high", "assurance_impact": "breaking",
    } for fid in ids]
    routed = [{"finding": f, "outcome": "combined", "rule_id": "shared"}
              for f in findings]
    event = {"assessment_key": "dtg:portfolio:combined:shared",
             "body": "\n".join("| " + chr(96) + fid + chr(96) +
                               " | source | change |" for fid in ids)}
    issue = {"number": 1194, "state": "open",
             "html_url": "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/1194",
             "body": "Findings " + ids[0] + " and " + ids[1]}
    candidate = {"schema": "rahp-toolkit-transfer-candidate/v1",
                 "toolkit_owner_issue": 1194, "finding_ids": list(ids)}
    return candidate, findings, routed, [event], [], issue, []


class LineageTests(unittest.TestCase):
    def test_complete_group_still_does_not_transfer_authority(self):
        report = audit.qualify(*inputs())
        self.assertEqual(report["candidate_finding_count"], 2)
        self.assertEqual(report["no_commit_pin_count"], 0)
        self.assertEqual(report["unbound_publisher_key_count"], 2)
        self.assertFalse(report["cutover_authorized"])

    def test_exact_publisher_marker_is_still_not_approval(self):
        args = list(inputs())
        args[5]["body"] += "\n<!-- rahp-assessment-key:dtg:portfolio:combined:shared -->"
        report = audit.qualify(*args)
        self.assertEqual(report["unbound_publisher_key_count"], 0)
        self.assertFalse(report["authority_transfer_accepted"])

    def test_pr_only_source_is_not_immutable_pin(self):
        args = list(inputs())
        args[1][0]["evidence_urls"] = ["https://github.com/example/source/pull/2"]
        report = audit.qualify(*args)
        self.assertEqual(report["no_commit_pin_count"], 1)

    def test_comment_only_reference_does_not_become_accepted_owner(self):
        args = list(inputs())
        args[5]["body"] = ""
        args[6].append({"body": "Additional finding " + "a" * 20})
        report = audit.qualify(*args)
        self.assertTrue(report["findings"][0]["issue_text_reference"])
        self.assertFalse(report["findings"][1]["issue_text_reference"])
        self.assertFalse(report["authority_transfer_accepted"])

    def test_wrong_owner_fails_closed(self):
        args = list(inputs())
        args[5]["number"] = 3
        with self.assertRaisesRegex(audit.LineageError, "owner"):
            audit.qualify(*args)

    def test_duplicate_generated_event_fails(self):
        args = list(inputs())
        args[3].append(copy.deepcopy(args[3][0]))
        with self.assertRaisesRegex(audit.LineageError, "uniquely"):
            audit.qualify(*args)

    def test_missing_member_of_generated_group_fails(self):
        args = list(inputs())
        args[3][0]["body"] = "| " + chr(96) + "a" * 20 + chr(96) + " | source |"
        with self.assertRaisesRegex(audit.LineageError, "uniquely"):
            audit.qualify(*args)

    def test_duplicate_candidate_finding_fails(self):
        args = list(inputs())
        args[0]["finding_ids"].append("a" * 20)
        with self.assertRaisesRegex(audit.LineageError, "duplicate"):
            audit.qualify(*args)

    def test_missing_source_cannot_become_case(self):
        args = list(inputs())
        args[0]["finding_ids"].append("d" * 20)
        result = audit.qualify(*args)
        self.assertIn("source_finding_absent", result["findings"][2]["blockers"])


if __name__ == "__main__":
    unittest.main()
