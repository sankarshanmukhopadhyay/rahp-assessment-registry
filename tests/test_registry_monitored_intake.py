import base64
import copy
import hashlib
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
    "toolkit_observation_revision": "d" * 40,
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
        self.review_event = {
            "assessment_key": KEY,
            "repository": "trustoverip/dtgwg-trust-tasks-tf",
            "new": "a" * 40,
            "title": "[RAHP review required] Reviewed source fixture",
            "body": "Material change requires a bounded assessment.",
            "labels": ["assessment-required", "dtg-instance"],
            "event_class": "assessment-required",
        }
        full_digest = hashlib.sha256(json.dumps(
            self.review_event, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")).hexdigest()
        self.manifest["event"]["source_evidence_sha256"] = full_digest
        self.manifest["event"]["finding_id"] = full_digest[:20]
        self.authority = {"schema": "rahp-registry-monitored-intake-authority/v1",
                          "admissions": [self.approval()]}
        self.policy = {"schema": "rahp-external-case-publication/v1", "owner": "registry"}
        self.rows = []
        self.posts = []
        self.disabled = True
        self.absent_registrations = set()
        self.workflow_states = {}
        self.reg = {"commit": {"sha": "c" * 40}}
        self.tk = {"commit": {"sha": "d" * 40}}

    def approval(self):
        event = self.manifest["event"]
        return {
            "assessment_key": event["assessment_key"], "case_id": event["case_id"],
            "manifest_path": PATH, "source_repository": event["source_repository"],
            "source_revision": event["source_revision"],
            "toolkit_observation_revision": event["toolkit_observation_revision"],
            "finding_id": event["finding_id"],
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
        if "/rahp-toolkit/contents/instances/dtg/generated/review-events.json" in url:
            return enc([self.review_event])
        if "/rahp-toolkit/compare/" in url:
            return {"status": "identical"}
        if "/commits/" in url:
            return {"sha": self.manifest["event"]["source_revision"]}
        if "/rahp-toolkit/issues?state=all" in url:
            return self.rows
        if "/rahp-toolkit/actions/workflows?" in url:
            workflows = [
                {"id": i + 1, "path": path,
                 "state": self.workflow_states.get(
                     path, "disabled_manually" if self.disabled else "active")}
                for i, path in enumerate(sorted(monitored.OLD_WORKFLOWS))
                if path not in self.absent_registrations
            ]
            return {"total_count": len(workflows), "workflows": workflows}
        if "/rahp-toolkit/actions/runs?" in url:
            return {"total_count": 0, "workflow_runs": []}
        self.fail("unexpected live authority read " + url)

    def test_only_actual_case_publisher_registrations_require_retirement(self):
        expected = {
            ".github/workflows/cross-spec-pressure-test.yml",
            ".github/workflows/distributed-resilience-assessment.yml",
            ".github/workflows/dtg-materiality-main.yml",
            ".github/workflows/instance-monitor-main.yml",
            ".github/workflows/dtg-portfolio-materiality-handoff.yml",
            ".github/workflows/instance-watch.yml",
        }
        self.assertEqual(monitored.OLD_WORKFLOWS, expected)
        self.assertNotIn(".github/workflows/review-workers.yml", expected)
        self.assertNotIn(".github/workflows/dpip-lifecycle.yml", expected)

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

    def test_observation_commit_requires_accepted_ancestry(self):
        original = self.fetch
        def diverged(url):
            if "/rahp-toolkit/compare/" in url:
                return {"status": "diverged"}
            return original(url)
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "not in accepted protected-main history"):
            monitored.qualify(self.manifest, PATH, "", fetch=diverged)
        malformed = copy.deepcopy(self.manifest)
        malformed["event"]["toolkit_observation_revision"] = "main"
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "pinned Toolkit observation commit"):
            monitored.qualify(malformed, PATH, "", fetch=self.fetch)
        # A current main descendant may accept evidence from a historic
        # approved ancestor whose review-event array has since changed.
        def advanced(url):
            if "/rahp-toolkit/compare/" in url:
                return {"status": "ahead"}
            if "/rahp-toolkit/branches/main" in url:
                return {"commit": {"sha": "e" * 40}}
            return original(url)
        receipt = monitored.qualify(self.manifest, PATH, "", fetch=advanced)
        self.assertEqual(receipt["accepted_source"]["accepted_toolkit_commit"],
                         "d" * 40)
        self.assertEqual(receipt["toolkit_main_sha"], "e" * 40)

    def test_wrong_accepted_source_digest_or_event_cannot_authorize_case(self):
        for changed in (
            {"body": "modified after approval"},
            {"new": "e" * 40},
            {"repository": "other/subject"},
            {"labels": ["change-triage"]},
            {"event_class": "change-triage"},
        ):
            with self.subTest(changed=changed):
                before = dict(self.review_event)
                self.review_event.update(changed)
                try:
                    with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                                "exact accepted material review"):
                        monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)
                finally:
                    self.review_event = before
        before = dict(self.review_event)
        self.review_event["assessment_key"] = "dtg:repository:wrong"
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "missing or duplicate accepted"):
            monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)
        self.review_event = before

    def test_unavailable_accepted_source_blocks_even_with_valid_approval(self):
        original = self.fetch
        def missing(url):
            if "/generated/review-events.json" in url:
                return enc([])
            return original(url)
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "missing or duplicate accepted"):
            monitored.qualify(self.manifest, PATH, "", fetch=missing)

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

    def test_absent_retired_workflows_qualify_with_four_disabled_current_writers(self):
        self.absent_registrations = set(monitored.RETIRED_WRITER_WORKFLOWS)
        receipt = monitored.run(self.manifest, PATH, "", fetch=self.fetch)
        self.assertEqual(receipt["state"], "qualified")
        self.assertEqual(
            {row["path"] for row in receipt["disabled_external_writer_registrations"]},
            monitored.CURRENT_WRITER_WORKFLOWS,
        )
        self.assertTrue(receipt["registered_external_writer_exclusion_verified"])

    def test_absent_current_publisher_is_not_writer_exclusion(self):
        for path in sorted(monitored.CURRENT_WRITER_WORKFLOWS):
            with self.subTest(path=path):
                self.absent_registrations = {path}
                with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                            "not demonstrably disabled"):
                    monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)
        self.absent_registrations.clear()

    def test_active_or_unknown_retired_registration_fails_closed(self):
        retired = sorted(monitored.RETIRED_WRITER_WORKFLOWS)[0]
        for state in ("active", "disabled_inactivity", "unknown"):
            with self.subTest(state=state):
                self.workflow_states[retired] = state
                with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                            "not demonstrably disabled"):
                    monitored.qualify(self.manifest, PATH, "", fetch=self.fetch)
        self.workflow_states.clear()

    def test_duplicate_retired_registration_fails_closed(self):
        retired = sorted(monitored.RETIRED_WRITER_WORKFLOWS)[0]
        original = self.fetch
        def duplicate(url):
            response = original(url)
            if "/actions/workflows?" not in url:
                return response
            rows = list(response["workflows"])
            rows.append(dict(next(row for row in rows if row["path"] == retired)))
            return {"total_count": len(rows), "workflows": rows}
        with self.assertRaisesRegex(monitored.MonitoredAdmissionError,
                                    "not demonstrably disabled"):
            monitored.qualify(self.manifest, PATH, "", fetch=duplicate)

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
                        current = sorted(monitored.CURRENT_WRITER_WORKFLOWS)[0]
                        rows = [row for row in rows if row["path"] != current]
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
        # The publish preflight must admit the same exact monitored receipt
        # schema emitted by the read-only qualify job.
        self.assertIn("'rahp-registry-monitored-intake-qualification/v1')", text)
        self.assertIn("assert receipt.get('schema') in (", text)
        self.assertIn("inputs.monitored_intake == true", text)
        self.assertIn("historical_execution_exclusion_proven') is not True", text)
        self.assertIn("registered_external_writer_exclusion_verified') is not True", text)
        self.assertIn("scripts/registry_monitored_intake.py", text)
        self.assertIn("if: inputs.direct_intake != true && inputs.monitored_intake != true", text)
        self.assertIn("if: inputs.direct_intake == true && inputs.monitored_intake != true", text)
        self.assertNotIn("  schedule:", text)


if __name__ == "__main__":
    unittest.main()
