import base64
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_monitored_intake as monitored
import registry_intake as intake

PATH = "outbox/pending/monitored-source-fixture.json"
KEY = "dtg:portfolio:combined:reviewed-fixture"
EVENT = {
    "kind": "external_assessment",
    "assessment_key": KEY,
    "case_id": "RAHP-AR-DTG-0999",
    "title": "Qualified monitored case fixture",
    "proposition": "A qualified source-specific proposition requires assessment.",
    "source_repository": "trustoverip/dtgwg-trust-tasks-tf",
    "source_revision": "a" * 40,
    "source_url": "https://github.com/trustoverip/dtgwg-trust-tasks-tf/commit/" + "a" * 40,
    "finding_id": "f" * 20,
    "responsible_owner": "trustoverip/dtgwg-trust-tasks-tf",
    "source_evidence_sha256": "b" * 64,
}
MANIFEST = {"schema": "rahp-registry-pending-intake/v1", "event": EVENT}


def enc(obj):
    return {"encoding": "base64", "content": base64.b64encode(
        json.dumps(obj).encode("utf-8")).decode("ascii")}


class MonitoredIntakeTests(unittest.TestCase):
    def setUp(self):
        self.manifest = copy.deepcopy(MANIFEST)
        self.authority = {"schema": "rahp-registry-monitored-intake-authority/v1",
                          "admissions": [self.approval()]}
        self.policy = {"schema": "rahp-external-case-publication/v1", "owner": "registry"}
        self.rows = []
        self.posts = []
        self.disabled = True
        self.reg = {"commit": {"sha": "c" * 40}}
        self.tk = {"commit": {"sha": "d" * 40}}

    def approval(self):
        event = self.manifest["event"]
        return {
            "assessment_key": event["assessment_key"], "case_id": event["case_id"],
            "manifest_path": PATH, "source_repository": event["source_repository"],
            "source_revision": event["source_revision"], "finding_id": event["finding_id"],
            "source_evidence_sha256": event["source_evidence_sha256"], "status": "approved",
        }

    def fetch(self, url):
        if "/rahp-assessment-registry/branches/main" in url:
            return self.reg
        if "/rahp-toolkit/branches/main" in url:
            return self.tk
        if "/rahp-assessment-registry/contents/" + PATH in url:
            return enc(self.manifest)
        if "/rahp-assessment-registry/contents/" + monitored.AUTH_PATH in url:
            return enc(self.authority)
        if "/rahp-toolkit/contents/" + monitored.POLICY_PATH in url:
            return enc(self.policy)
        if "/commits/" in url:
            return {"sha": self.manifest["event"]["source_revision"]}
        if "/rahp-toolkit/issues?state=all" in url:
            return self.rows
        if "/rahp-toolkit/actions/workflows?" in url:
            workflows = [
                {"id": i + 1, "path": path,
                 "state": "disabled_manually" if self.disabled else "active"}
                for i, path in enumerate(sorted(monitored.OLD_WORKFLOWS))
            ]
            return {"total_count": len(workflows), "workflows": workflows}
        if "/rahp-toolkit/actions/runs?" in url:
            return {"total_count": 0, "workflow_runs": []}
        self.fail("unexpected live authority read " + url)

    def test_valid_approved_source_qualifies_without_mutation_or_assurance(self):
        result = monitored.run(self.manifest, PATH, "", fetch=self.fetch)
        self.assertEqual(result["state"], "qualified")
        self.assertEqual(result["assessment_key"], KEY)
        self.assertTrue(result["toolkit_current_policy_is_registry"])
        self.assertTrue(result["toolkit_writers_quiescent_at_observation"])
        self.assertTrue(result["historical_execution_exclusion_proven"])
        self.assertTrue(result["registered_external_writer_exclusion_verified"])
        self.assertEqual(len(result["disabled_external_writer_registrations"]),
                         len(monitored.OLD_WORKFLOWS))
        self.assertFalse(result["cross_repository_atomic_lock_proven"])
        self.assertIsNone(result["assurance_determination"])
        self.assertEqual(self.posts, [])

    def test_toolkit_remains_authoritative_rejects_new_case_before_post(self):
        self.policy["owner"] = "toolkit"
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError, "has not assigned"):
            monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                          post=lambda _: self.fail("no unqualified write"))

    def test_existing_toolkit_owner_requires_governed_transfer(self):
        self.rows = [{"number": 272, "state": "closed",
                      "body": "<!-- rahp-assessment-key:" + KEY + " -->"}]
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError, "already owns"):
            monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)

    def test_duplicate_or_withdrawn_governance_authority_fails_closed(self):
        for changed in (self.approval(), {**self.approval(), "status": "withdrawn"},
                        {**self.approval(), "source_evidence_sha256": "c" * 64}):
            self.authority["admissions"] = [self.approval(), changed] if changed == self.approval() else [changed]
            with self.subTest(changed=changed), self.assertRaisesRegex(
                    monitored.MonitoredAdmissionError, "approved monitored"):
                monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)

    def test_bad_source_proof_and_wrong_namespace_fail_before_effect(self):
        for field, value in (
            ("source_revision", "main"),
            ("source_evidence_sha256", "not-a-sha"),
            ("assessment_key", "external:direct:not-monitored"),
            ("case_id", ""),
            ("controller_issue_url", "https://github.com/sankarshanmukhopadhyay/rahp-toolkit/issues/2"),
            ("responsible_owner", "some-other/repo"),
        ):
            altered = copy.deepcopy(self.manifest)
            altered["event"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                monitored.qualify(altered, PATH, "", fetch=self.fetch)
        with self.assertRaises(ValueError):
            monitored.qualify(self.manifest, "../outside.json", "", fetch=self.fetch)

    def test_registered_external_writer_must_be_disabled_server_side(self):
        self.disabled = False
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "not demonstrably disabled"):
            monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                          post=lambda _: self.fail("must not publish"))

    def test_missing_or_duplicate_writer_registration_is_not_exclusion(self):
        original = self.fetch
        for variant in ("missing", "duplicate", "incomplete"):
            with self.subTest(variant=variant):
                def invalid(url):
                    result = original(url)
                    if "/actions/workflows?" not in url:
                        return result
                    rows = list(result["workflows"])
                    if variant == "missing":
                        rows.pop()
                    elif variant == "duplicate":
                        rows.append(dict(rows[0]))
                    else:
                        return {"total_count": 3, "workflows": rows}
                    return {"total_count": len(rows), "workflows": rows}
                with self.assertRaises(monitored.MonitoredAdmissionError):
                    monitored.qualify(self.manifest, PATH, "", fetch=invalid)

    def test_active_toolkit_external_writer_blocks_admission(self):
        original = self.fetch
        def active(url):
            if "/actions/runs?status=in_progress" in url:
                return {"total_count": 1, "workflow_runs": [{
                    "id": 123, "path": ".github/workflows/instance-monitor-main.yml",
                    "status": "in_progress",
                }]}
            return original(url)
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError, "active Toolkit"):
            monitored.qualify(self.manifest, PATH, "", fetch=active)

    def test_qualified_delivery_requires_unique_owner_reread(self):
        ev = self.manifest["event"]
        issue = {"number": 93, "state": "open",
                 "html_url": "https://github.com/" + intake.REGISTRY + "/issues/93",
                 "body": intake.render_body(ev)}
        before = iter([[], [issue]])
        def post(payload):
            self.posts.append(payload)
            return {"number": 93, "html_url": issue["html_url"]}
        result = monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                               load_issues=lambda: next(before), post=post)
        self.assertEqual(result["state"], "owner_observed")
        self.assertEqual(result["owner_number"], 93)
        self.assertEqual(len(self.posts), 1)
        self.assertFalse(result["first_case_execution"])
        self.assertIsNone(result["assurance_determination"])

    def test_existing_owner_requires_same_monitored_source_digest(self):
        ev = self.manifest["event"]
        owner = {
            "number": 92, "state": "open",
            "html_url": "https://github.com/" + intake.REGISTRY + "/issues/92",
            "body": intake.render_body({
                **ev, "source_evidence_sha256": "c" * 64,
            }),
        }
        with self.assertRaisesRegex(ValueError, "source evidence digest"):
            monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                          load_issues=lambda: [owner],
                          post=lambda _: self.fail("must not create duplicate"))

    def test_post_ambiguity_recovers_without_duplicate(self):
        ev = self.manifest["event"]
        owner = {"number": 94, "state": "open", "body": intake.render_body(ev),
                 "html_url": "https://github.com/" + intake.REGISTRY + "/issues/94"}
        reads = iter([[], [owner]])
        def ambiguous(_):
            raise intake.IntakeError("timed out after upstream commit")
        result = monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                               load_issues=lambda: next(reads), post=ambiguous)
        self.assertTrue(result["recovered_after_ambiguous_post"])
        self.assertEqual(result["owner_number"], 94)

    def test_unacknowledged_remote_delivery_stays_unresolved(self):
        reads = iter([[], []])
        with self.assertRaisesRegex(ValueError, "no authoritative"):
            monitored.run(self.manifest, PATH, "", apply=True, fetch=self.fetch,
                          load_issues=lambda: next(reads),
                          post=lambda _: {"number": 99, "html_url": "ignored"})

    def test_workflow_does_not_allow_unproven_monitored_publish(self):
        text = (ROOT / ".github/workflows/registry-outbox-replay.yml").read_text()
        self.assertIn("monitored_intake:", text)
        self.assertIn("inputs.monitored_intake == true", text)
        self.assertIn("historical_execution_exclusion_proven') is not True", text)
        self.assertIn("registered_external_writer_exclusion_verified') is not True", text)
        self.assertIn("scripts/registry_monitored_intake.py", text)
        self.assertIn("if: inputs.direct_intake != true && inputs.monitored_intake != true", text)
        self.assertIn("if: inputs.direct_intake == true && inputs.monitored_intake != true", text)
        self.assertNotIn("  schedule:", text)


if __name__ == "__main__":
    unittest.main()
